"""Polite, allowlisted HTTP fetching.

Rules from the source audit: identify ourselves, respect robots.txt on the Platinum hosts,
keep a gap between requests, back off on HTTP 429 (the site rate-limits), never follow a
redirect to a host outside the allowlist, and cap response size.
"""

from __future__ import annotations

import hashlib
import http.client
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

USER_AGENT = "KantahanCatalog/0.1 (+https://github.com/thekovie/kantahan; local ingestion)"
ALLOWED_SUFFIXES = ("platinumkaraoke.com", "platinumkaraoke.ph", "mediafire.com", "cdn.shopify.com")
ROBOTS_SUFFIXES = ("platinumkaraoke.com", "platinumkaraoke.ph")
MAX_BYTES = 50 * 1024 * 1024
MIN_DELAY = 3.0
MAX_REDIRECTS = 5
MAX_RETRIES = 4
RETRY_CAP = 300.0
TIMEOUT = 60.0  # per socket operation
TOTAL_TIMEOUT = 300.0  # whole response, against slow-loris servers
CHUNK = 64 * 1024
RETRYABLE_STATUS = (429, 503)


class FetchError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class HostNotAllowedError(FetchError):
    pass


@dataclass(frozen=True)
class Response:
    url: str  # final URL after redirects
    status: int
    content_type: str
    body: bytes


Transport = Callable[[str, Mapping[str, str]], Response]


def _host_matches(host: str, suffixes: tuple[str, ...]) -> bool:
    return any(host == s or host.endswith("." + s) for s in suffixes)


_HOSTNAME = re.compile(r"[a-z0-9]([a-z0-9.-]*[a-z0-9])?", re.ASCII)


def host_allowed(url: str) -> bool:
    """https only, an allowlisted host, no credentials, default port, no parser-confusing chars.

    Strict on purpose: the allowlist check and the HTTP client must agree on the host.
    """
    if url != url.strip() or "\\" in url or any(c.isspace() for c in url):
        return False
    try:
        parts = urlparse(url)
        port = parts.port
    except ValueError:
        return False
    host = parts.hostname or ""
    return (
        parts.scheme == "https"
        and parts.username is None
        and port in (None, 443)
        and _HOSTNAME.fullmatch(host) is not None
        and _host_matches(host, ALLOWED_SUFFIXES)
    )


class _GuardedRedirects(urllib.request.HTTPRedirectHandler):
    max_redirections = MAX_REDIRECTS

    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        if not host_allowed(newurl):
            raise HostNotAllowedError(f"redirect to a host outside the allowlist: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def urllib_transport(url: str, headers: Mapping[str, str]) -> Response:
    opener = urllib.request.build_opener(_GuardedRedirects)
    request = urllib.request.Request(url, headers=dict(headers))  # noqa: S310 (scheme checked)
    deadline = time.monotonic() + TOTAL_TIMEOUT
    with opener.open(request, timeout=TIMEOUT) as resp:
        chunks: list[bytes] = []
        size = 0
        while size <= MAX_BYTES:
            if time.monotonic() > deadline:
                raise FetchError(f"response took longer than {TOTAL_TIMEOUT:.0f}s: {url}")
            chunk = resp.read(min(CHUNK, MAX_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        return Response(
            resp.geturl(), resp.status, resp.headers.get("Content-Type", ""), b"".join(chunks)
        )


class Fetcher:
    def __init__(
        self,
        transport: Transport = urllib_transport,
        sleep: Callable[[float], None] = time.sleep,
        delay: float = MIN_DELAY,
    ) -> None:
        self._transport = transport
        self._sleep = sleep
        self._delay = delay
        self._requests = 0
        self._robots: dict[str, RobotFileParser] = {}

    def get(self, url: str) -> Response:
        if not host_allowed(url):
            raise HostNotAllowedError(f"host not on the allowlist: {url}")
        if not self._robots_allow(url):
            raise FetchError(f"disallowed by robots.txt: {url}")
        resp = self._request(url)
        if resp.url != url and not self._robots_allow(resp.url):
            raise FetchError(f"redirect target disallowed by robots.txt: {resp.url}")
        return resp

    def _request(self, url: str) -> Response:
        headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
        for attempt in range(MAX_RETRIES + 1):
            if self._requests:
                self._sleep(self._delay)
            self._requests += 1
            try:
                resp = self._transport(url, headers)
            except urllib.error.HTTPError as exc:
                if exc.code not in RETRYABLE_STATUS:
                    raise FetchError(f"HTTP {exc.code} for {url}", exc.code) from exc
                self._sleep(_retry_wait(exc.headers, attempt))
                continue
            except (
                urllib.error.URLError,
                TimeoutError,
                ConnectionError,
                http.client.HTTPException,
            ):
                self._sleep(min(5.0 * 2**attempt, RETRY_CAP))
                continue
            if not host_allowed(resp.url):
                raise HostNotAllowedError(f"redirected outside the allowlist: {resp.url}")
            if len(resp.body) > MAX_BYTES:
                raise FetchError(f"response larger than {MAX_BYTES} bytes: {url}")
            return resp
        raise FetchError(f"gave up after {MAX_RETRIES + 1} attempts: {url}")

    def _robots_allow(self, url: str) -> bool:
        host = urlparse(url).hostname or ""
        if not _host_matches(host, ROBOTS_SUFFIXES):
            return True
        if host not in self._robots:
            parser = RobotFileParser()
            try:
                resp = self._request(f"https://{host}/robots.txt")
                parser.parse(resp.body.decode("utf-8", "replace").splitlines())
            except FetchError as exc:
                if exc.status != 404:
                    raise
                parser.parse([])
            self._robots[host] = parser
        return self._robots[host].can_fetch(USER_AGENT, url)

    def download_pdf(self, url: str, dest: str | Path) -> tuple[str, int]:
        """Fetch a PDF into `dest` atomically. Returns (sha256, size)."""
        resp = self.get(url)
        if not resp.body.startswith(b"%PDF-"):
            raise FetchError(f"not a PDF ({resp.content_type or 'unknown type'}): {url}")
        target = Path(dest)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".part")
        tmp.write_bytes(resp.body)
        os.replace(tmp, target)
        return hashlib.sha256(resp.body).hexdigest(), len(resp.body)


def _retry_wait(headers: Any, attempt: int) -> float:
    value = str((headers or {}).get("Retry-After", ""))
    if value.isdigit():
        return min(float(value), RETRY_CAP)
    return float(min(60.0 * 2**attempt, RETRY_CAP))
