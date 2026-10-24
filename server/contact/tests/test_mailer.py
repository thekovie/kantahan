import importlib
import sys
from email.message import EmailMessage

import pytest
from conftest import make_settings

from kantahan_contact import mailer


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.timeout, self.context = host, port, timeout, context
        self.calls: list[str] = []
        self.sent: list[EmailMessage] = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(f"login:{user}")

    def send_message(self, message):
        self.sent.append(message)


@pytest.fixture
def fake(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", FakeSMTP)
    return FakeSMTP


def message():
    msg = EmailMessage()
    msg["To"] = "owner@example.net"
    msg.set_content("hello")
    return msg


def test_starttls_then_login_then_send(fake):
    mailer.smtp_sender(make_settings(smtp_security="starttls"))(message())
    client = fake.instances[0]
    assert client.calls == ["starttls", "login:user"] and len(client.sent) == 1
    assert client.timeout == mailer.SMTP_TIMEOUT and client.port == 587


def test_implicit_tls_skips_starttls(fake):
    mailer.smtp_sender(make_settings(smtp_security="ssl", smtp_port=465))(message())
    assert fake.instances[0].calls == ["login:user"] and fake.instances[0].context is not None


def test_no_security_and_no_login_for_a_local_relay(fake):
    sender = mailer.smtp_sender(
        make_settings(smtp_security="none", smtp_user=None, smtp_password=None)
    )
    sender(message())
    assert fake.instances[0].calls == [] and len(fake.instances[0].sent) == 1


def test_the_entry_point_refuses_to_start_without_settings(monkeypatch):
    for name in ("SMTP_HOST", "SMTP_FROM", "CONTACT_TO", "ALLOWED_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    sys.modules.pop("kantahan_contact.main", None)
    with pytest.raises(Exception, match="SMTP_HOST"):
        importlib.import_module("kantahan_contact.main")


def test_the_entry_point_builds_the_app_from_the_environment(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example")
    monkeypatch.setenv("SMTP_FROM", "contact@kantahan.example")
    monkeypatch.setenv("CONTACT_TO", "owner@example.net")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://kantahan.example")
    sys.modules.pop("kantahan_contact.main", None)
    assert importlib.import_module("kantahan_contact.main").app is not None
