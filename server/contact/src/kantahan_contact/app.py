"""POST /api/contact: validate, throttle, relay by e-mail. Collects the least it can.

Order of checks: size, origin, content type, rate limit, JSON, fields, honeypot, send. Every
rejection is a constant message: nothing the visitor typed is echoed, and nothing private (the
destination address, SMTP details, the message, the visitor's address) is logged or returned.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import re
import time
import unicodedata
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from .mailer import Form, Sender, build_message
from .ratelimit import SlidingWindow
from .settings import Settings

log = logging.getLogger("kantahan.contact")
MAX_BODY_BYTES = 16 * 1024
HOUR = 3600.0
TYPES = ("removal", "correction", "other")
MIN_MESSAGE_CHARS = 10
MAX_NAME_CHARS = 80
MAX_REFERENCE_CHARS = 200
MAX_EMAIL_CHARS = 254
# Visitor addresses are checked conservatively (ASCII, one plain address); the field is optional.
VISITOR_ADDRESS = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
# Control characters, line and paragraph separators, and surrogates.
_BREAKS = ("Cc", "Zl", "Zp", "Cs")


def _has_breaks(text: str, allow: str = "") -> bool:
    return any(unicodedata.category(c) in _BREAKS and c not in allow for c in text)


def _reply(status: int, payload: dict[str, Any], headers: dict[str, str] | None = None) -> Response:
    return JSONResponse(payload, status_code=status, headers=headers)


def _fail(status: int, error: str, **extra: Any) -> Response:
    return _reply(status, {"ok": False, "error": error, **extra})


def _single_line(value: Any, limit: int) -> str | None:
    if not isinstance(value, str) or len(value) > limit or _has_breaks(value):
        raise ValueError
    return value.strip() or None


def _validate(data: dict[str, Any], limit: int) -> tuple[Form | None, dict[str, str]]:
    fields: dict[str, str] = {}
    kind = data.get("type")
    if kind not in TYPES:
        fields["type"] = "Choose what this is about."
    message = data.get("message")
    cleaned = ""
    if not isinstance(message, str):
        fields["message"] = "Write a message."
    else:
        text = message.replace("\r\n", "\n").replace("\r", "\n")
        # Keep line breaks and tabs; drop other control characters and separators that a mail reader
        # could show as line breaks. A lone surrogate cannot be encoded at all, so it is refused.
        cleaned = "".join(c for c in text if not _has_breaks(c, allow="\n\t")).strip()
        if any(unicodedata.category(c) == "Cs" for c in text):
            fields["message"] = "This message has characters that are not allowed."
        elif len(cleaned) < MIN_MESSAGE_CHARS:
            fields["message"] = f"Write at least {MIN_MESSAGE_CHARS} characters."
        elif len(cleaned) > limit:
            fields["message"] = f"Keep it under {limit} characters."
    parsed: dict[str, str | None] = {}
    for name, cap in (
        ("name", MAX_NAME_CHARS),
        ("reference", MAX_REFERENCE_CHARS),
        ("email", MAX_EMAIL_CHARS),
    ):
        raw = data.get(name)
        if raw in (None, ""):
            parsed[name] = None
            continue
        try:
            parsed[name] = _single_line(raw, cap)
        except ValueError:
            fields[name] = "This field has characters that are not allowed or is too long."
            continue
        if name == "email" and parsed[name] and not VISITOR_ADDRESS.match(parsed[name] or ""):
            fields["email"] = "Enter a valid e-mail address, or leave it empty."
    if fields:
        return None, fields
    return Form(str(kind), cleaned, parsed["email"], parsed["name"], parsed["reference"]), {}


def create_app(
    settings: Settings, sender: Sender, clock: Callable[[], float] = time.monotonic
) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    per_ip = SlidingWindow(settings.rate_per_ip_hour, HOUR, clock)
    overall = SlidingWindow(settings.rate_global_hour, HOUR, clock)

    @app.middleware("http")
    async def harden(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def client_key(request: Request) -> str:
        address = request.client.host if request.client else "unknown"
        if settings.trust_proxy_headers:
            address = request.headers.get("x-real-ip", "").strip() or address
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            return address
        if isinstance(
            parsed, ipaddress.IPv6Address
        ):  # one visitor can use any address in their /64
            return str(ipaddress.ip_network(f"{parsed}/64", strict=False))
        return str(parsed)

    @app.get("/api/health")
    async def health() -> Response:
        return _reply(200, {"ok": True})

    @app.post("/api/contact")
    async def contact(request: Request) -> Response:
        if request.headers.get("origin") not in settings.allowed_origins:
            return _reject(403, "forbidden")
        media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if media_type != "application/json":
            return _reject(415, "unsupported")
        announced = request.headers.get("content-length", "")
        if announced.isascii() and announced.isdigit() and int(announced) > MAX_BODY_BYTES:
            return _reject(413, "too_large")
        key = client_key(request)
        wait = max(per_ip.check(key), overall.check("all"))
        if wait:
            log.info("contact rejected: rate_limited")
            return _reply(429, {"ok": False, "error": "rate_limited"}, {"Retry-After": str(wait)})
        per_ip.record(key)
        overall.record("all")
        chunks: list[bytes] = []
        size = 0
        async for chunk in request.stream():  # stops reading as soon as the cap is passed
            size += len(chunk)
            if size > MAX_BODY_BYTES:
                return _reject(413, "too_large")
            chunks.append(chunk)
        body = b"".join(chunks)
        try:
            data = json.loads(body)
        except ValueError:
            return _reject(422, "invalid_body")
        if not isinstance(data, dict):
            return _reject(422, "invalid_body")
        form, fields = _validate(data, settings.max_message_chars)
        if form is None:
            log.info("contact rejected: invalid_fields")
            return _fail(422, "invalid_fields", fields=fields)
        if data.get("website"):  # a hidden field only a script fills in
            log.info("contact rejected: honeypot")
            return _reply(202, {"ok": True})
        try:
            await run_in_threadpool(sender, build_message(settings, form))
        except Exception as exc:  # the cause may name hosts or accounts; keep only its type
            log.error("contact failed: %s", type(exc).__name__)
            return _fail(503, "unavailable")
        log.info("contact accepted: %s", form.type)
        return _reply(202, {"ok": True})

    def _reject(status: int, error: str) -> Response:
        log.info("contact rejected: %s", error)
        return _fail(status, error)

    return app
