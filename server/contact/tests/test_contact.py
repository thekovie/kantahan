import json
import logging

import pytest
from conftest import ORIGIN, make_settings

from kantahan_contact.settings import SettingsError, load_settings

URL = "/api/contact"


def test_a_valid_request_is_relayed_by_mail_and_accepted(client, sent, valid):
    response = client.post(URL, json=valid)
    assert response.status_code == 202 and response.json() == {"ok": True}
    assert len(sent) == 1
    message = sent[0]
    assert message["To"] == "owner-private@example.net"
    assert message["From"] == "Kantahan <contact@kantahan.example>"
    assert message["Reply-To"] == "someone@example.org"
    assert message["Subject"] == "[Kantahan] Correction request"
    body = message.get_content()
    assert "Song 00589 lists the wrong artist" in body and "Reyna, 00589" in body


def test_the_destination_address_never_appears_in_a_response(client, valid):
    text = client.post(URL, json=valid).text + client.get("/api/health").text
    assert "owner-private" not in text and "example.net" not in text


def test_email_and_name_are_optional(client, sent, valid):
    for field in ("email", "name", "reference"):
        valid.pop(field)
    assert client.post(URL, json=valid).status_code == 202
    assert sent[0]["Reply-To"] is None


@pytest.mark.parametrize(
    ("patch", "field"),
    [
        ({"type": "spam"}, "type"),
        ({"message": "short"}, "message"),
        ({"message": "x" * 501}, "message"),
        ({"email": "not-an-email"}, "email"),
        ({"email": "a@b.co\r\nBcc: victim@example.org"}, "email"),
        ({"name": "Eve\r\nBcc: victim@example.org"}, "name"),
        ({"reference": "x\nInjected: header"}, "reference"),
        ({"name": "n" * 81}, "name"),
    ],
)
def test_invalid_input_is_rejected_per_field_without_echoing_it(client, sent, valid, patch, field):
    response = client.post(URL, json={**valid, **patch})
    assert response.status_code == 422
    body = response.json()
    assert body["ok"] is False and field in body["fields"]
    assert "Bcc" not in response.text and "victim" not in response.text
    assert sent == []


def test_a_message_may_have_several_lines_and_control_characters_are_removed(client, sent, valid):
    valid["message"] = "Line one is long enough.\n\nLine two\x00 with a NUL and a tab\t."
    assert client.post(URL, json=valid).status_code == 202
    body = sent[0].get_content()
    assert "\x00" not in body and "Line two" in body and "\n\n" in body


def test_a_filled_honeypot_looks_accepted_but_sends_nothing(client, sent, valid):
    response = client.post(URL, json={**valid, "website": "http://spam.example"})
    assert response.status_code == 202 and response.json() == {"ok": True}
    assert sent == []


def test_each_address_may_send_only_a_few_requests_per_hour(client, sent, clock, valid):
    for _ in range(3):
        assert client.post(URL, json=valid).status_code == 202
    blocked = client.post(URL, json=valid)
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) > 0
    assert len(sent) == 3
    clock.now += 3601
    assert client.post(URL, json=valid).status_code == 202


def test_there_is_also_a_ceiling_for_all_addresses_together(make_client, sent, valid):
    client = make_client(trust_proxy_headers=True, rate_per_ip_hour=10)
    for i in range(5):
        response = client.post(URL, json=valid, headers={"X-Real-IP": f"198.51.100.{i}"})
        assert response.status_code == 202
    assert client.post(URL, json=valid, headers={"X-Real-IP": "198.51.100.99"}).status_code == 429


def test_the_forwarded_address_is_used_only_when_a_proxy_is_trusted(make_client, valid):
    untrusted = make_client(rate_per_ip_hour=1)
    assert untrusted.post(URL, json=valid, headers={"X-Real-IP": "198.51.100.1"}).status_code == 202
    assert untrusted.post(URL, json=valid, headers={"X-Real-IP": "198.51.100.2"}).status_code == 429
    trusted = make_client(rate_per_ip_hour=1, trust_proxy_headers=True)
    assert trusted.post(URL, json=valid, headers={"X-Real-IP": "198.51.100.1"}).status_code == 202
    assert trusted.post(URL, json=valid, headers={"X-Real-IP": "198.51.100.2"}).status_code == 202
    assert trusted.post(URL, json=valid, headers={"X-Real-IP": "198.51.100.1"}).status_code == 429


@pytest.mark.parametrize("origin", ["https://evil.example", "http://kantahan.example", "null"])
def test_requests_from_other_origins_are_refused(client, sent, valid, origin):
    response = client.post(URL, json=valid, headers={"Origin": origin})
    assert response.status_code == 403 and sent == []


def test_a_request_without_an_origin_is_refused(make_client, sent, valid):
    client = make_client()
    client.headers.pop("Origin")
    assert client.post(URL, json=valid).status_code == 403 and sent == []


def test_only_json_is_accepted(client, valid):
    response = client.post(URL, content=json.dumps(valid), headers={"Content-Type": "text/plain"})
    assert response.status_code == 415
    broken = client.post(URL, content="{not json", headers={"Content-Type": "application/json"})
    assert broken.status_code == 422
    listed = client.post(URL, json=[valid])
    assert listed.status_code == 422


def test_an_oversized_body_is_refused_before_it_is_parsed(client, valid):
    huge = {**valid, "message": "x" * 100_000}
    assert client.post(URL, json=huge).status_code == 413


def test_other_methods_are_not_allowed(client):
    assert client.get(URL).status_code == 405
    assert client.get("/api/health").json() == {"ok": True}


def test_a_mail_failure_is_reported_generically_and_not_leaked(make_client, valid, caplog):
    def broken(_message):
        raise OSError("smtp.example:587 refused the password secret-password for user")

    client = make_client(sender=broken)
    response = client.post(URL, json=valid)
    assert response.status_code == 503 and response.json()["error"] == "unavailable"
    assert "secret-password" not in response.text and "smtp" not in response.text.lower()
    assert "secret-password" not in caplog.text


def test_logs_hold_no_personal_data(client, valid, caplog):
    client.post(URL, json=valid)
    client.post(URL, json={**valid, "website": "spam"})
    client.post(URL, json={**valid, "email": "bad"})
    logged = caplog.text
    for private in ("someone@example.org", "A Person", "00589", "owner-private", "testclient"):
        assert private not in logged
    assert any(r.name == "kantahan.contact" for r in caplog.records)


def test_headers_say_this_is_not_cacheable_or_sniffable(client, valid):
    response = client.post(URL, json=valid)
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


ENV = {
    "SMTP_HOST": "smtp.example",
    "SMTP_FROM": "contact@kantahan.example",
    "CONTACT_TO": "owner@example.net",
    "ALLOWED_ORIGINS": "https://kantahan.example, https://www.kantahan.example",
}


def test_settings_load_from_the_environment_with_defaults():
    settings = load_settings(ENV)
    assert settings.smtp_port == 587 and settings.smtp_security == "starttls"
    assert settings.allowed_origins == {"https://kantahan.example", "https://www.kantahan.example"}
    assert settings.rate_per_ip_hour == 5 and settings.trust_proxy_headers is False


def test_settings_read_the_password_from_a_secret_file(tmp_path):
    secret = tmp_path / "smtp_password"
    secret.write_text("from-file\n")
    settings = load_settings({**ENV, "SMTP_PASSWORD_FILE": str(secret), "SMTP_USER": "u"})
    assert settings.smtp_password == "from-file"


@pytest.mark.parametrize("missing", ["SMTP_HOST", "SMTP_FROM", "CONTACT_TO", "ALLOWED_ORIGINS"])
def test_missing_settings_stop_the_service_at_startup_and_name_the_variable(missing):
    env = {k: v for k, v in ENV.items() if k != missing}
    with pytest.raises(SettingsError, match=missing):
        load_settings(env)


@pytest.mark.parametrize(
    "bad",
    [
        {"SMTP_PORT": "abc"},
        {"SMTP_SECURITY": "plaintext-forever"},
        {"ALLOWED_ORIGINS": "kantahan.example"},
        {"ALLOWED_ORIGINS": "http://kantahan.example"},
        {"CONTACT_TO": "not an address"},
        {"CONTACT_TO": "a@b.co\nBcc: x@y.zz"},
        {"RATE_PER_IP_HOUR": "0"},
    ],
)
def test_bad_settings_are_rejected(bad):
    with pytest.raises(SettingsError):
        load_settings({**ENV, **bad})


def test_plain_http_origin_is_allowed_only_for_localhost_development():
    settings = load_settings({**ENV, "ALLOWED_ORIGINS": "http://localhost:5173"})
    assert "http://localhost:5173" in settings.allowed_origins


def test_the_logger_name_is_stable():
    assert logging.getLogger("kantahan.contact").name == "kantahan.contact"
    assert make_settings().contact_to.endswith("example.net") and ORIGIN
