import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from conftest import sample_rows
from pdfgen import make_pdf
from test_cli import PDF_URL, SOURCES, Site

from kantahan_catalog import cli, db, runner
from kantahan_catalog.fetch import Fetcher

PAGE_A = b'<script src="//platinumkaraoke.com/cdn/shop/t/50/assets/songlist-update-data.js?v=1"></script>'
SCRIPT = (
    'const songList=[{product:"REYNA SERIES",volumes:[{volume:1,link:"' + PDF_URL + '"}]}],x=1;'
).encode()
PAGE_B = (
    b'<button class="accordion4">REYNA SERIES</button><table><tr><td>VOLUME 1</td><td><a href="'
    + PDF_URL.encode()
    + b'">x</a></td></tr></table>'
)
DISPLAY = (
    "source: {label: Test source, url: 'https://example.test/s'}\n"
    "models:\n  reyna: {name: Reyna, family: Reyna series, hue: magenta}\n"
)


@pytest.fixture
def world(tmp_path):
    work = tmp_path / "work"
    (tmp_path / "sources.yaml").write_text(SOURCES)
    (tmp_path / "display.yaml").write_text(DISPLAY)
    pdf = Path(
        make_pdf(tmp_path / "src.pdf", [[sample_rows(15000, 5)]], header="Vol. 1 For Reyna ! 1")
    )
    pages = {
        "https://platinumkaraoke.com/pages/songlist-update": PAGE_A,
        "https://platinumkaraoke.com/cdn/shop/t/50/assets/songlist-update-data.js?v=1": SCRIPT,
        "https://platinumkaraoke.com/pages/songlist-update-old": PAGE_B,
        "https://platinumkaraoke.ph/updates/Songlist%20Update.html": b"<html></html>",
        PDF_URL: pdf.read_bytes(),
    }
    site = Site(pages)
    lines: list[str] = []

    def run(*argv):
        code = cli.main(
            [
                "--work",
                str(work),
                "--sources",
                str(tmp_path / "sources.yaml"),
                "--display",
                str(tmp_path / "display.yaml"),
                *argv,
            ],
            fetcher=Fetcher(site, sleep=lambda s: None),
            out=lines.append,
        )
        return code, "\n".join(lines)

    return run, work, pages, lines


def manifest(work):
    return json.loads((work / "publish" / "manifest.json").read_text())


def test_manual_run_goes_from_discovery_to_a_published_catalog(world):
    run, work, _, _ = world
    code, text = run("run", "--manual")
    assert code == 0 and "published v1" in text
    assert manifest(work)["models"][0]["songs"] == 5
    conn = db.connect(work / "catalog.sqlite")
    row = conn.execute("SELECT kind, outcome FROM import_run").fetchone()
    assert (row["kind"], row["outcome"]) == ("manual", "published")


def test_a_second_run_finds_nothing_new(world):
    run, work, _, _ = world
    run("run", "--manual")
    code, text = run("run", "--manual")
    assert code == 0 and "unchanged" in text
    assert not (work / "publish" / "v2").exists()


def test_scheduled_runs_wait_for_the_interval(world):
    run, work, _, _ = world
    assert run("run")[0] == 0 and manifest(work)["version"] == "v1"
    code, text = run("run")
    assert code == 0 and "not due" in text
    code, text = run("run", "--min-interval-days", "0")
    assert code == 0 and "unchanged" in text


def test_is_due_uses_the_last_successful_scheduled_run():
    conn = db.connect(":memory:")
    db.migrate(conn)
    now = datetime(2026, 11, 1, tzinfo=UTC)
    assert runner.is_due(conn, 14, now)
    run_id = runner.start_run(conn, "scheduled", now - timedelta(days=20))
    runner.finish_run(conn, run_id, "error", {}, now - timedelta(days=20))
    assert runner.is_due(conn, 14, now)
    run_id = runner.start_run(conn, "scheduled", now - timedelta(days=3))
    runner.finish_run(conn, run_id, "published", {}, now - timedelta(days=3))
    assert not runner.is_due(conn, 14, now)
    assert runner.is_due(conn, 2, now)


def test_two_runs_cannot_overlap(tmp_path):
    with runner.run_lock(tmp_path), pytest.raises(runner.RunLocked):
        with runner.run_lock(tmp_path):
            pass
    with runner.run_lock(tmp_path):  # released afterwards
        pass


def test_a_failed_fetch_with_nothing_else_publishes_nothing(world):
    run, work, pages, _ = world
    pages[PDF_URL] = b"not a pdf"
    code, text = run("run", "--manual")
    assert code == 1 and "FAILED" in text and "nothing to publish" in text
    assert not (work / "publish" / "manifest.json").exists()


def test_one_dead_link_does_not_block_a_new_volume_but_the_run_is_partial(world):
    run, work, pages, _ = world
    assert run("run", "--manual")[0] == 0
    dead = "https://www.mediafire.com/file/key002/Gone.pdf/file"
    pages["https://platinumkaraoke.com/cdn/shop/t/50/assets/songlist-update-data.js?v=1"] = (
        'const songList=[{product:"REYNA SERIES",volumes:[{volume:1,link:"'
        + PDF_URL
        + '"},{volume:2,link:"'
        + dead
        + '"}]}],x=1;'
    ).encode()
    pages[dead] = b"<html>gone</html>"
    code, text = run("run", "--manual")
    assert code == 1 and "continuing with what is available" in text
    conn = db.connect(work / "catalog.sqlite")
    last = conn.execute("SELECT outcome FROM import_run ORDER BY id DESC").fetchone()[0]
    assert last == "partial"
    assert runner.is_due(conn, 14) is True  # a partial scheduled run is not a success: retry soon


def test_suspend_works_while_a_run_holds_the_lock(world):
    run, work, _, _ = world
    run("run", "--manual")
    with runner.run_lock(work):
        assert run("suspend", "--notice", "Paused.")[0] == 0
        assert manifest(work)["suspended"] is True
        assert run("resume")[0] == 0
        assert run("rollback", "v1")[0] == 1  # rollback still waits its turn


def test_audit_without_discovery_says_what_to_do(world):
    run, _, _, _ = world
    code, text = run("audit")
    assert code == 1 and "run `discover` first" in text


def test_audit_reports_a_document_that_changed_behind_its_link(world, tmp_path):
    run, _, pages, _ = world
    run("run", "--manual")
    assert run("audit")[0] == 0
    pages[PDF_URL] = Path(
        make_pdf(tmp_path / "new.pdf", [[sample_rows(15000, 6)]], header="Vol. 1 For Reyna ! 1")
    ).read_bytes()
    code, text = run("audit")
    assert code == 2 and "CHANGED" in text and "Volume 1" in text


def test_admin_commands_suspend_rollback_and_withdraw(world):
    run, work, _, _ = world
    run("run", "--manual")
    assert run("suspend", "--notice", "Paused for review.")[0] == 0
    assert manifest(work)["suspended"] is True
    assert run("resume")[0] == 0 and manifest(work)["suspended"] is False
    assert run("rollback", "v1")[0] == 0
    code, text = run("rollback", "v7")
    assert code == 1 and "no such version" in text
    code, text = run("withdraw", "--release", "Volume 1")
    assert (
        code == 1 and "nothing to publish" in text
    )  # the only volume left: refuse an empty catalog


def test_a_run_covers_every_publisher_section_and_a_new_one_only_warns(world, tmp_path):
    run, work, pages, _ = world
    bravo_pdf = "https://www.mediafire.com/file/bravo01/Bravo_Volume_1.pdf/file"
    new_pdf = "https://www.mediafire.com/file/newsec1/New_Section_Volume_1.pdf/file"
    script = (
        'const songList=[{product:"REYNA SERIES",volumes:[{volume:1,link:"' + PDF_URL + '"}]},'
        '{product:"BRAVO",volumes:[{volume:1,link:"' + bravo_pdf + '"}]},'
        '{product:"BRAND NEW MACHINES",volumes:[{volume:1,link:"' + new_pdf + '"}]}],x=1;'
    ).encode()
    pages["https://platinumkaraoke.com/cdn/shop/t/50/assets/songlist-update-data.js?v=1"] = script
    pdf2 = make_pdf(tmp_path / "b.pdf", [[sample_rows(20000, 4)]], header="Vol. 1 ! 1")
    pages[bravo_pdf] = Path(pdf2).read_bytes()
    pages[new_pdf] = Path(pdf2).read_bytes()
    code, text = run("run", "--manual")
    assert code == 0 and "BRAND NEW MACHINES" in text and "no model yet" in text
    conn = db.connect(work / "catalog.sqlite")
    mapped = {
        r[0]
        for r in conn.execute(
            "SELECT m.slug FROM release_model rm JOIN model m ON m.id = rm.model_id"
        )
    }
    assert "bravo" in mapped  # the section is fetched, imported and mapped without being named
    assert manifest(work)["models"][0]["slug"] == "reyna"  # bravo has no display entry, so it waits


def test_map_command_reports_and_never_fails_for_an_unknown_section(world):
    run, work, _, _ = world
    run("run", "--manual")
    code, text = run("map")
    assert code == 0 and "map:" in text


def test_backup_and_restore_drill_through_the_command_line(world, tmp_path):
    run, work, _, _ = world
    run("run", "--manual")
    backups = tmp_path / "backups"
    code, text = run("backup", "--to", str(backups))
    assert code == 0 and "backup written" in text
    live = manifest(work)

    import shutil

    shutil.rmtree(work / "publish")
    (work / "catalog.sqlite").unlink()
    code, text = run("restore", str(next(backups.iterdir())))
    assert code == 2 and "--yes" in text and not (work / "publish").exists()

    code, text = run("restore", str(next(backups.iterdir())), "--yes")
    assert code == 0 and "restored" in text and "predate withdrawals" in text
    assert manifest(work) == live
    code, text = run("publish")
    assert code == 0 and "unchanged" in text


def test_restoring_a_missing_backup_fails_clearly(world, tmp_path):
    run, _, _, _ = world
    code, text = run("restore", str(tmp_path / "nope"), "--yes")
    assert code == 1 and "not a backup" in text
