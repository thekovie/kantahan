"""Turn a validated form into an e-mail and send it. Nothing from the form reaches a header."""

from __future__ import annotations

import smtplib
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from email.message import EmailMessage

from .settings import Settings

Sender = Callable[[EmailMessage], None]
SMTP_TIMEOUT = 10.0
SUBJECTS = {
    "removal": "[Kantahan] Removal request",
    "correction": "[Kantahan] Correction request",
    "other": "[Kantahan] Message",
}


@dataclass(frozen=True)
class Form:
    type: str
    message: str
    email: str | None
    name: str | None
    reference: str | None


def build_message(settings: Settings, form: Form) -> EmailMessage:
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = settings.contact_to
    message["Subject"] = SUBJECTS[form.type]
    if form.email:
        message["Reply-To"] = form.email  # validated: one address, no line breaks
    lines = [
        f"Type: {form.type}",
        f"Name: {form.name or '-'}",
        f"E-mail: {form.email or '-'}",
        f"About: {form.reference or '-'}",
        "",
        form.message,
    ]
    message.set_content("\n".join(lines))
    return message


def smtp_sender(settings: Settings) -> Sender:
    def send(message: EmailMessage) -> None:
        context = ssl.create_default_context()
        if settings.smtp_security == "ssl":
            client: smtplib.SMTP = smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT, context=context
            )
        else:
            client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT)
        with client:
            if settings.smtp_security == "starttls":
                client.starttls(context=context)
            if settings.smtp_user and settings.smtp_password:
                client.login(settings.smtp_user, settings.smtp_password)
            client.send_message(message)

    return send
