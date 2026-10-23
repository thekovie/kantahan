import hashlib
import urllib.error

import pytest

from kantahan_catalog import fetch
from kantahan_catalog.fetch import Fetcher, FetchError, HostNotAllowedError, Response, host_allowed

PDF = b"%PDF-1.4 fake"
OK_URL = "https://www.mediafire.com/file/abc/x.pdf/file"


class Script:
    """A fake transport that replays queued outcomes (responses or exceptions)."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, url, headers):
        self.calls.append((url, dict(headers)))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def pdf_response(url=OK_URL, body=PDF):
    return Response(url, 200, "application/pdf", body)


def http_error(code, retry_after=None):
    headers = {"Retry-After": retry_after} if retry_after else {}
    return urllib.error.HTTPError("u", code, "x", headers, None)


def make(*outcomes, **kw):
    sleeps = []
    transport = Script(*outcomes)
    return Fetcher(transport, sleep=sleeps.append, delay=2.0, **kw), transport, sleeps


@pytest.mark.parametrize(
    ("url", "ok"),
    [
        ("https://platinumkaraoke.com/pages/songlist-update", True),
        ("https://www.mediafire.com/file/x", True),
        ("https://download1321.mediafire.com/a/b.pdf", True),
        ("https://cdn.shopify.com/s/files/x.pdf", True),
        ("https://evilmediafire.com/x", False),
        ("https://mediafire.com.evil.test/x", False),
        ("file:///etc/passwd", False),
        ("https://example.test/", False),
    ],
)
def test_host_allowlist(url, ok):
    assert host_allowed(url) is ok


def test_disallowed_host_is_rejected_before_any_request():
    f, transport, _ = make()
    with pytest.raises(HostNotAllowedError):
        f.get("https://example.test/x")
    assert transport.calls == []


def test_user_agent_identifies_the_project():
    f, transport, _ = make(pdf_response())
    f.get(OK_URL)
    assert "kantahan" in transport.calls[0][1]["User-Agent"].lower()


def test_gap_between_requests_but_not_before_the_first():
    f, _, sleeps = make(pdf_response(), pdf_response())
    f.get(OK_URL)
    assert sleeps == []
    f.get(OK_URL)
    assert sleeps == [2.0]


def test_http_429_waits_for_retry_after_then_succeeds():
    f, transport, sleeps = make(http_error(429, "7"), pdf_response())
    assert f.get(OK_URL).status == 200
    assert 7.0 in sleeps and len(transport.calls) == 2


def test_connection_reset_is_retried():
    f, _, _ = make(ConnectionResetError("empty reply"), pdf_response())
    assert f.get(OK_URL).status == 200


def test_gives_up_after_repeated_rate_limiting():
    f, transport, _ = make(*[http_error(429)] * (fetch.MAX_RETRIES + 1))
    with pytest.raises(FetchError, match="gave up"):
        f.get(OK_URL)
    assert len(transport.calls) == fetch.MAX_RETRIES + 1


def test_not_found_is_not_retried():
    f, transport, _ = make(http_error(404))
    with pytest.raises(FetchError, match="HTTP 404"):
        f.get(OK_URL)
    assert len(transport.calls) == 1


def test_redirect_to_a_foreign_host_is_rejected():
    f, _, _ = make(pdf_response(url="https://example.test/landing"))
    with pytest.raises(HostNotAllowedError):
        f.get(OK_URL)


def test_oversized_response_is_rejected(monkeypatch):
    monkeypatch.setattr(fetch, "MAX_BYTES", 10)
    f, _, _ = make(pdf_response(body=b"%PDF-" + b"x" * 20))
    with pytest.raises(FetchError, match="larger"):
        f.get(OK_URL)


def test_download_pdf_writes_atomically_and_returns_hash(tmp_path):
    f, _, _ = make(pdf_response())
    sha, size = f.download_pdf(OK_URL, tmp_path / "pdfs" / "a.pdf")
    assert (tmp_path / "pdfs" / "a.pdf").read_bytes() == PDF
    assert sha == hashlib.sha256(PDF).hexdigest() and size == len(PDF)
    assert not list((tmp_path / "pdfs").glob("*.part"))


def test_download_rejects_non_pdf_content(tmp_path):
    f, _, _ = make(Response(OK_URL, 200, "text/html", b"<html>login</html>"))
    with pytest.raises(FetchError, match="not a PDF"):
        f.download_pdf(OK_URL, tmp_path / "a.pdf")
    assert not (tmp_path / "a.pdf").exists()


def test_robots_txt_is_respected_on_platinum_hosts():
    robots = Response(
        "https://platinumkaraoke.com/robots.txt",
        200,
        "text/plain",
        b"User-agent: *\nDisallow: /private/\n",
    )
    page = Response("https://platinumkaraoke.com/pages/ok", 200, "text/html", b"ok")
    f, transport, _ = make(robots, page)
    assert f.get("https://platinumkaraoke.com/pages/ok").body == b"ok"
    with pytest.raises(FetchError, match="robots"):
        f.get("https://platinumkaraoke.com/private/x")
    assert len(transport.calls) == 2  # robots.txt fetched once and cached


def test_missing_robots_txt_means_allowed():
    page = Response("https://platinumkaraoke.ph/a", 200, "text/html", b"ok")
    f, _, _ = make(http_error(404), page)
    assert f.get("https://platinumkaraoke.ph/a").body == b"ok"


@pytest.mark.parametrize(
    "url",
    [
        "http://www.mediafire.com/file/x",  # plain http
        "https://mediafire.com@evil.test/x",
        "https://user:pw@mediafire.com/x",
        "https://evil.test\\@mediafire.com/x",
        "https://mediafire.com:8443/x",
        "https://mediafire.com:99999/x",
        " https://mediafire.com/x",
        "https://mediafire.com/x y",
        "https://mediafire.com./x",
        "https://exa mple.mediafire.com/x",
    ],
)
def test_strict_url_checks_reject_parser_confusion(url):
    assert host_allowed(url) is False


def test_default_https_port_is_fine():
    assert host_allowed("https://www.mediafire.com:443/file/x")


def test_fetch_errors_carry_the_http_status():
    f, _, _ = make(http_error(404))
    with pytest.raises(FetchError) as info:
        f.get(OK_URL)
    assert info.value.status == 404


def test_redirect_target_is_checked_against_robots_too():
    robots = Response(
        "https://platinumkaraoke.com/robots.txt",
        200,
        "text/plain",
        b"User-agent: *\nDisallow: /private/\n",
    )
    redirected = Response("https://platinumkaraoke.com/private/x", 200, "text/html", b"no")
    f, _, _ = make(robots, redirected)
    with pytest.raises(FetchError, match="redirect target disallowed"):
        f.get("https://platinumkaraoke.com/pages/ok")


def test_redirect_guard_blocks_foreign_hosts_and_allows_listed_ones():
    import urllib.request

    guard = fetch._GuardedRedirects()
    req = urllib.request.Request(OK_URL)
    with pytest.raises(HostNotAllowedError):
        guard.redirect_request(req, None, 302, "Found", {}, "https://evil.test/x")
    new = guard.redirect_request(
        req, None, 302, "Found", {}, "https://download1.mediafire.com/a.pdf"
    )
    assert new is not None and new.full_url.startswith("https://download1.mediafire.com")


class FakeHttpResponse:
    status = 200
    headers = {"Content-Type": "application/pdf"}

    def __init__(self, data):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def geturl(self):
        return OK_URL

    def read(self, n):
        chunk, self._data = self._data[:n], self._data[n:]
        return chunk


class FakeOpener:
    def __init__(self, data):
        self.data = data

    def open(self, request, timeout):
        return FakeHttpResponse(self.data)


def patch_opener(monkeypatch, data):
    monkeypatch.setattr(fetch.urllib.request, "build_opener", lambda *a: FakeOpener(data))


def test_transport_reads_everything_under_the_cap(monkeypatch):
    patch_opener(monkeypatch, b"%PDF-" + b"x" * 200_000)
    assert len(fetch.urllib_transport(OK_URL, {}).body) == 200_005


def test_transport_stops_reading_at_the_size_cap(monkeypatch):
    monkeypatch.setattr(fetch, "MAX_BYTES", 1000)
    patch_opener(monkeypatch, b"x" * 50_000)
    assert len(fetch.urllib_transport(OK_URL, {}).body) == 1001  # one over the cap, then rejected


def test_transport_gives_up_on_a_response_that_takes_too_long(monkeypatch):
    patch_opener(monkeypatch, b"x" * 200_000)
    clock = iter([0.0, 0.0, 999.0, 999.0, 999.0])
    monkeypatch.setattr(fetch.time, "monotonic", lambda: next(clock))
    with pytest.raises(FetchError, match="took longer"):
        fetch.urllib_transport(OK_URL, {})
