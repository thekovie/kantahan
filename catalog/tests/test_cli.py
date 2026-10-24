import json
from pathlib import Path

import pytest
from conftest import sample_rows
from pdfgen import make_pdf

from kantahan_catalog import cli, db
from kantahan_catalog.fetch import Fetcher, Response

SOURCES = """sources:
  - {id: A, url: "https://platinumkaraoke.com/pages/songlist-update", priority: P0}
  - {id: B, url: "https://platinumkaraoke.com/pages/songlist-update-old", priority: P0}
  - {id: C, url: "https://platinumkaraoke.ph/updates/Songlist%20Update.html", priority: P1}
"""
PDF_URL = "https://www.mediafire.com/file/key001/Reyna_Volume_1.pdf/file"
ROBOTS = b"User-agent: *\nAllow: /\n"


class Site:
    """Fake web: URL -> bytes. Records the order of requests."""

    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def __call__(self, url, headers):
        self.calls.append(url)
        if url.endswith("/robots.txt"):
            return Response(url, 200, "text/plain", ROBOTS)
        return Response(
            url, 200, "application/pdf" if url == PDF_URL else "text/html", self.pages[url]
        )


@pytest.fixture
def env(tmp_path):
    work = tmp_path / "work"
    sources = tmp_path / "sources.yaml"
    sources.write_text(SOURCES)
    lines: list[str] = []
    return work, sources, lines


def run(env, *argv, fetcher=None):
    work, sources, lines = env
    code = cli.main(
        ["--work", str(work), "--sources", str(sources), *argv], fetcher=fetcher, out=lines.append
    )
    return code, "\n".join(lines)


def test_migrate_then_revert(env):
    assert run(env, "migrate")[1].endswith("[1, 2, 3, 4, 5]")
    assert run(env, "migrate", "--down", "1")[1].endswith("[5]")


def test_full_local_flow_discover_fetch_import_build(env, tmp_path):
    work, _, _ = env
    page_a = b'<script src="//platinumkaraoke.com/cdn/shop/t/50/assets/songlist-update-data.js?v=1"></script>'
    script = (
        'const songList=[{product:"REYNA SERIES",volumes:[{volume:1,link:"' + PDF_URL + '"}]}],x=1;'
    ).encode()
    page_b = (
        b'<button class="accordion4">REYNA SERIES</button><table><tr><td>VOLUME 1</td><td><a href="'
        + PDF_URL.encode()
        + b'">x</a></td></tr></table>'
    )
    pdf_path = make_pdf(
        tmp_path / "src.pdf", [[sample_rows(15000, 5)]], header="Vol. 1 For Reyna ! 1"
    )
    site = Site(
        {
            "https://platinumkaraoke.com/pages/songlist-update": page_a,
            "https://platinumkaraoke.com/cdn/shop/t/50/assets/songlist-update-data.js?v=1": script,
            "https://platinumkaraoke.com/pages/songlist-update-old": page_b,
            "https://platinumkaraoke.ph/updates/Songlist%20Update.html": b"<html></html>",
            PDF_URL: Path(pdf_path).read_bytes(),
        }
    )
    fetcher = Fetcher(site, sleep=lambda s: None)

    assert run(env, "discover", fetcher=fetcher)[0] == 0
    discovered = json.loads((work / "discovered.json").read_text())
    assert {d["source"] for d in discovered} == {"a", "b"} and len(discovered) == 2

    assert run(env, "fetch", fetcher=fetcher)[0] == 0
    assert (work / "pdfs" / "key001.pdf").exists()
    assert run(env, "fetch", fetcher=fetcher)[1].endswith("already present 1, failed 0")

    assert "imported 1" in run(env, "import")[1]
    assert "unchanged 1" in run(env, "import")[1]
    stats = run(env, "stats")[1]
    assert "releases mapped: 1, songs 5" in stats

    code, text = run(env, "build")
    assert code == 0 and text.splitlines()[-1].startswith("validated: 5 songs")
    assert json.loads((work / "releases" / "reyna.json").read_text())["count"] == 5


def test_discover_reports_removed_links_on_second_run(env):
    work, _, _ = env
    page_a = b'<script src="https://platinumkaraoke.com/cdn/x/songlist-update-data.js"></script>'
    one = b'const songList=[{product:"S",volumes:[{volume:1,link:"https://www.mediafire.com/file/a/x.pdf/file"},{volume:2,link:"https://www.mediafire.com/file/b/y.pdf/file"}]}];'
    two = b'const songList=[{product:"S",volumes:[{volume:1,link:"https://www.mediafire.com/file/a/x.pdf/file"}]}];'
    pages = {
        "https://platinumkaraoke.com/pages/songlist-update": page_a,
        "https://platinumkaraoke.com/cdn/x/songlist-update-data.js": one,
        "https://platinumkaraoke.com/pages/songlist-update-old": b"",
        "https://platinumkaraoke.ph/updates/Songlist%20Update.html": b"",
    }
    run(env, "discover", fetcher=Fetcher(Site(pages), sleep=lambda s: None))
    pages["https://platinumkaraoke.com/cdn/x/songlist-update-data.js"] = two
    code, text = run(env, "discover", fetcher=Fetcher(Site(pages), sleep=lambda s: None))
    assert "removed 1" in text and "REMOVED a S Volume 2" in text


def test_import_without_download_says_what_to_do(env):
    work, _, _ = env
    work.mkdir(parents=True, exist_ok=True)
    from kantahan_catalog.discover import DiscoveredLink, save_links

    save_links(
        work / "discovered.json",
        [
            DiscoveredLink(
                "a", "REYNA SERIES", "Volume 9", "https://www.mediafire.com/file/zzz/f.pdf/file"
            )
        ],
    )
    assert "MISSING Volume 9: run fetch first" in run(env, "import")[1]


def test_build_with_nothing_imported_fails_cleanly(env):
    run(env, "migrate")
    code, text = run(env, "build")
    assert code == 1 and "no mapped releases" in text


def test_build_with_conflicts_exits_2(env, tmp_path):
    work, _, _ = env
    run(env, "migrate")
    conn = db.connect(work / "catalog.sqlite")
    from kantahan_catalog.importer import ensure_source, import_pdf

    ensure_source(conn, "a", "https://x", "P0")
    one = make_pdf(tmp_path / "1.pdf", [[[("15001", "Original", "A"), ("15002", "Fine", "A")]]])
    two = make_pdf(tmp_path / "2.pdf", [[[("15001", "Changed", "A"), ("15003", "New", "A")]]])
    import_pdf(
        conn,
        one,
        source_slug="a",
        url="https://www.mediafire.com/file/k1/a.pdf/file",
        label="Volume 1",
    )
    import_pdf(
        conn,
        two,
        source_slug="a",
        url="https://www.mediafire.com/file/k2/b.pdf/file",
        label="Volume 2",
    )
    conn.close()
    assert run(env, "build")[0] == 2


def test_uppercase_source_ids_are_accepted_and_unknown_ones_fail_cleanly(env, tmp_path):
    from kantahan_catalog.discover import DiscoveredLink, save_links

    work, _, _ = env
    link = DiscoveredLink("a", "REYNA SERIES", "Volume 1", PDF_URL)
    save_links(work / "discovered.json", [link])
    (work / "pdfs").mkdir(parents=True)
    src = make_pdf(tmp_path / "src.pdf", [[sample_rows(15000, 3)]])
    (work / "pdfs" / "key001.pdf").write_bytes(Path(src).read_bytes())
    assert "imported 1" in run(env, "import", "--from", "A")[1]
    code, text = run(env, "import", "--from", "zzz")
    assert code == 1 and "unknown source 'zzz'" in text
