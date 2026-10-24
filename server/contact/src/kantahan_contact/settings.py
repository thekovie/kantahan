"""Settings come from environment variables only and are checked once at startup."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from email.utils import parseaddr
from pathlib import Path

ADDRESS = re.compile(r"^[^@\s<>\r\n]+@[^@\s<>\r\n]+\.[^@\s<>\r\n]+$")
ORIGIN = re.compile(r"^(https://[A-Za-z0-9.-]+(:\d+)?|http://(localhost|127\.0\.0\.1)(:\d+)?)$")
SECURITY = ("starttls", "ssl", "none")


class SettingsError(Exception):
    """One or more settings are missing or wrong. The message names every variable."""


@dataclass(frozen=True)
class Settings:
    smtp_host: str
    smtp_port: int
    smtp_user: str | None
    smtp_password: str | None
    smtp_security: str
    mail_from: str
    contact_to: str
    allowed_origins: frozenset[str]
    rate_per_ip_hour: int = 5
    rate_global_hour: int = 60
    max_message_chars: int = 2000
    trust_proxy_headers: bool = False


def _int(
    env: Mapping[str, str], name: str, default: int, low: int, high: int, errors: list[str]
) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        errors.append(f"{name} must be a whole number")
        return default
    if not low <= value <= high:
        errors.append(f"{name} must be between {low} and {high}")
    return value


def _secret(env: Mapping[str, str], name: str, errors: list[str]) -> str | None:
    """A value from NAME, or from the file named by NAME_FILE (Docker and Compose secrets)."""
    path = env.get(f"{name}_FILE", "").strip()
    if path:
        try:
            return Path(path).read_text(encoding="utf-8").strip() or None
        except OSError:
            errors.append(f"{name}_FILE cannot be read")
            return None
    return env.get(name, "").strip() or None


def load_settings(env: Mapping[str, str]) -> Settings:
    errors: list[str] = []
    host = env.get("SMTP_HOST", "").strip()
    if not host:
        errors.append("SMTP_HOST is required")
    mail_from = env.get("SMTP_FROM", "").strip()
    if not mail_from or not ADDRESS.match(parseaddr(mail_from)[1]) or "\n" in mail_from:
        errors.append("SMTP_FROM is required and must be an address (optionally 'Name <address>')")
    to = env.get("CONTACT_TO", "").strip()
    if not to:
        errors.append("CONTACT_TO is required")
    elif not ADDRESS.match(to):
        errors.append("CONTACT_TO must be a single e-mail address")
    origins = frozenset(o.strip() for o in env.get("ALLOWED_ORIGINS", "").split(",") if o.strip())
    if not origins:
        errors.append(
            "ALLOWED_ORIGINS is required (the site's address, for example https://example.org)"
        )
    for origin in origins:
        if not ORIGIN.match(origin):
            errors.append(
                f"ALLOWED_ORIGINS has {origin!r}: use https://host (http only for localhost)"
            )
    security = env.get("SMTP_SECURITY", "starttls").strip().lower()
    if security not in SECURITY:
        errors.append(f"SMTP_SECURITY must be one of {', '.join(SECURITY)}")
    user = env.get("SMTP_USER", "").strip() or None
    password = _secret(env, "SMTP_PASSWORD", errors)
    if user and not password:
        errors.append("SMTP_PASSWORD (or SMTP_PASSWORD_FILE) is required when SMTP_USER is set")
    settings = Settings(
        smtp_host=host,
        smtp_port=_int(env, "SMTP_PORT", 587, 1, 65535, errors),
        smtp_user=user,
        smtp_password=password,
        smtp_security=security,
        mail_from=mail_from,
        contact_to=to,
        allowed_origins=origins,
        rate_per_ip_hour=_int(env, "RATE_PER_IP_HOUR", 5, 1, 1000, errors),
        rate_global_hour=_int(env, "RATE_GLOBAL_HOUR", 60, 1, 100000, errors),
        max_message_chars=_int(env, "MAX_MESSAGE_CHARS", 2000, 50, 10000, errors),
        trust_proxy_headers=env.get("TRUST_PROXY_HEADERS", "").strip().lower()
        in ("1", "true", "yes"),
    )
    if errors:
        raise SettingsError("; ".join(errors))
    return settings
