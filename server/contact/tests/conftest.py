import logging
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient

from kantahan_contact.app import create_app
from kantahan_contact.settings import Settings

ORIGIN = "https://kantahan.example"


def make_settings(**overrides):
    base = {
        "smtp_host": "smtp.example",
        "smtp_port": 587,
        "smtp_user": "user",
        "smtp_password": "secret-password",
        "smtp_security": "starttls",
        "mail_from": "Kantahan <contact@kantahan.example>",
        "contact_to": "owner-private@example.net",
        "allowed_origins": frozenset({ORIGIN}),
        "rate_per_ip_hour": 3,
        "rate_global_hour": 5,
        "max_message_chars": 500,
        "trust_proxy_headers": False,
    }
    return Settings(**{**base, **overrides})


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def sent():
    return []


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def make_client(sent, clock):
    def build(sender=None, **overrides):
        def capture(message: EmailMessage) -> None:
            sent.append(message)

        app = create_app(make_settings(**overrides), sender or capture, clock)
        return TestClient(app, headers={"Origin": ORIGIN})

    return build


@pytest.fixture
def client(make_client):
    return make_client()


@pytest.fixture
def valid():
    return {
        "type": "correction",
        "message": "Song 00589 lists the wrong artist for the Reyna songbook.",
        "email": "someone@example.org",
        "name": "A Person",
        "reference": "Reyna, 00589",
        "website": "",
    }


@pytest.fixture(autouse=True)
def quiet_logs(caplog):
    caplog.set_level(logging.DEBUG)
