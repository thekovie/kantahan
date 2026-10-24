import hashlib
import io
import shutil
import sqlite3
import tarfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from conftest import sample_rows
from test_publish import DISPLAY, add

from kantahan_catalog import backup as backup_module
from kantahan_catalog import db
from kantahan_catalog.backup import BackupError, list_backups, make_backup, restore_backup
from kantahan_catalog.publish import publish, read_manifest, set_suspended, withdraw_release

T0 = datetime(2026, 11, 1, 3, 0, tzinfo=UTC)


@pytest.fixture
def site(tmp_path, pdf):
    """A work folder with a real database and a published catalog, like a running server."""
    work, out = tmp_path / "work", tmp_path / "publish"
    work.mkdir()
    conn = db.connect(work / "catalog.sqlite")
    db.migrate(conn)
    from kantahan_catalog.importer import ensure_source

    ensure_source(conn, "a", "https://example.test/a", "P0")
    add(conn, pdf("a.pdf", sample_rows(15000, 50)), 1)
    publish(conn, out, DISPLAY)
    add(conn, pdf("b.pdf", sample_rows(16000, 50)), 2)
    publish(conn, out, DISPLAY)
    conn.close()
    return work, out


def tree(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_a_backup_holds_a_consistent_database_and_the_published_catalog(site, tmp_path):
    work, out = site
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    assert path.name == "kantahan-20261101T030000Z"
    assert {p.name for p in path.iterdir()} == {
        "catalog.sqlite",
        "publish.tar.gz",
        "checksums.sha256",
    }
    copy = sqlite3.connect(path / "catalog.sqlite")
    assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert copy.execute("SELECT count(*) FROM song_entry").fetchone()[0] == 100
    with tarfile.open(path / "publish.tar.gz") as archive:
        names = set(archive.getnames())
    assert "manifest.json" in names and "v1/reyna.json" in names and "v2/reyna.json" in names
    assert not [n for n in names if ".staging" in n or n.endswith(".part")]


def test_old_backups_are_pruned_but_the_new_one_never_is(site, tmp_path):
    work, out = site
    dest = tmp_path / "backups"
    for day in range(5):
        make_backup(work, out, dest, keep=3, now=T0 + timedelta(days=day))
    kept = [p.name for p in list_backups(dest)]
    assert kept == [f"kantahan-202611{d:02d}T030000Z" for d in (3, 4, 5)]
    make_backup(work, out, dest, keep=1, now=T0 + timedelta(days=9))
    assert [p.name for p in list_backups(dest)] == ["kantahan-20261110T030000Z"]


def test_two_backups_in_the_same_second_do_not_overwrite_each_other(site, tmp_path):
    work, out = site
    make_backup(work, out, tmp_path / "b", now=T0)
    with pytest.raises(BackupError, match="already exists"):
        make_backup(work, out, tmp_path / "b", now=T0)


def test_restore_rebuilds_the_database_and_the_published_catalog_from_nothing(site, tmp_path):
    work, out = site
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    before_manifest, before_tree = read_manifest(out), tree(out)
    shutil.rmtree(work)
    shutil.rmtree(out)
    work.mkdir()
    out.mkdir()

    summary = restore_backup(path, work, out, now=T0 + timedelta(hours=1))
    assert summary.live_version == "v2" and summary.versions == ("v1", "v2")
    assert read_manifest(out) == before_manifest and tree(out) == before_tree
    conn = db.connect(work / "catalog.sqlite")
    assert conn.execute("SELECT count(*) FROM song_entry").fetchone()[0] == 100
    # The drill's real test: publishing again from the restored database changes nothing.
    assert publish(conn, out, DISPLAY).outcome == "unchanged"


def test_restore_keeps_what_it_replaces_outside_the_served_folder(site, tmp_path):
    work, out = site
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    conn = db.connect(work / "catalog.sqlite")
    conn.execute("DELETE FROM song_entry WHERE number = '15001'")
    conn.commit()
    conn.close()
    summary = restore_backup(path, work, out, now=T0 + timedelta(hours=1))
    aside = summary.kept_aside
    assert aside is not None and aside.is_dir() and not aside.is_relative_to(out)
    assert (aside / "catalog.sqlite").exists()
    restored = sqlite3.connect(work / "catalog.sqlite")
    assert (
        restored.execute("SELECT count(*) FROM song_entry WHERE number = '15001'").fetchone()[0]
        == 1
    )


def test_a_damaged_backup_is_refused_and_nothing_changes(site, tmp_path):
    work, out = site
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    before_db, before_tree = (work / "catalog.sqlite").read_bytes(), tree(out)
    raw = bytearray((path / "publish.tar.gz").read_bytes())
    raw[len(raw) // 2] ^= 0xFF
    (path / "publish.tar.gz").write_bytes(bytes(raw))
    with pytest.raises(BackupError, match="checksum"):
        restore_backup(path, work, out, now=T0)
    assert (work / "catalog.sqlite").read_bytes() == before_db and tree(out) == before_tree


def test_a_missing_or_incomplete_backup_is_refused(site, tmp_path):
    work, out = site
    with pytest.raises(BackupError, match="not a backup"):
        restore_backup(tmp_path / "nothing", work, out)
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    (path / "checksums.sha256").unlink()
    with pytest.raises(BackupError, match="checksum"):
        restore_backup(path, work, out)


def _archive_with(member: tarfile.TarInfo, data: bytes = b"x") -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        archive.addfile(member, io.BytesIO(data))
    return buffer.getvalue()


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../escape.txt", tarfile.REGTYPE),
        ("/abs.txt", tarfile.REGTYPE),
        ("v1/link", tarfile.SYMTYPE),
    ],
)
def test_unsafe_archive_members_are_never_extracted(site, tmp_path, name, kind):
    work, out = site
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    member = tarfile.TarInfo(name)
    member.type = kind
    member.linkname = "/etc/passwd" if kind == tarfile.SYMTYPE else ""
    member.size = 1 if kind == tarfile.REGTYPE else 0
    evil = _archive_with(member)
    (path / "publish.tar.gz").write_bytes(evil)
    (path / "checksums.sha256").write_text(
        "".join(
            f"{hashlib.sha256((path / f).read_bytes()).hexdigest()}  {f}\n"
            for f in ("catalog.sqlite", "publish.tar.gz")
        )
    )
    with pytest.raises(BackupError, match="unsafe"):
        restore_backup(path, work, out)
    assert not (tmp_path / "escape.txt").exists()


def _withdraw_and_pause(work, out, notice="Paused for review."):
    """What the owner does after a takedown request: withdraw a volume, publish, pause."""
    conn = db.connect(work / "catalog.sqlite")
    models = withdraw_release(conn, label="Volume 2")
    result = publish(conn, out, DISPLAY, allow_drop=frozenset(models), keep=1)
    set_suspended(conn, out, True, notice=notice)
    conn.close()
    return result.version


def test_a_restore_never_undoes_a_takedown(site, tmp_path):
    work, out = site
    backup = make_backup(work, out, tmp_path / "backups", now=T0)  # taken before the request
    live_version = _withdraw_and_pause(work, out)
    assert live_version == "v3" and sorted(p.name for p in out.iterdir() if p.is_dir()) == ["v3"]

    summary = restore_backup(backup, work, out, now=T0 + timedelta(days=3))

    manifest = read_manifest(out)
    assert manifest["version"] == "v3" and manifest["suspended"] is True
    assert manifest["notice"] == "Paused for review."
    assert sorted(p.name for p in out.iterdir() if p.is_dir()) == [
        "v3"
    ]  # v1 and v2 held the volume
    assert summary.skipped == ("v1", "v2") and summary.versions == ()
    conn = db.connect(work / "catalog.sqlite")
    withdrawn = conn.execute("SELECT label FROM release WHERE withdrawn_at IS NOT NULL").fetchall()
    assert [r[0] for r in withdrawn] == ["Volume 2"]
    actions = [r[0] for r in conn.execute("SELECT action FROM publication_event ORDER BY id")]
    assert actions == ["withdraw", "suspend"]
    # the next publish still leaves the withdrawn volume out, and does not collide with v3
    assert publish(conn, out, DISPLAY).outcome == "unchanged"
    assert read_manifest(out)["models"][0]["songs"] == 50


def test_restored_publication_numbers_continue_after_what_is_on_the_server(site, tmp_path, pdf):
    work, out = site
    backup = make_backup(work, out, tmp_path / "backups", now=T0)
    _withdraw_and_pause(work, out)
    restore_backup(backup, work, out, now=T0)
    conn = db.connect(work / "catalog.sqlite")
    add(conn, pdf("c.pdf", sample_rows(17000, 20)), 3)
    result = publish(conn, out, DISPLAY, allow_drop=True)
    assert result.version == "v4"  # never reuses v3 or lower


def test_a_pause_set_after_the_backup_survives_a_restore(site, tmp_path):
    work, out = site
    backup = make_backup(work, out, tmp_path / "backups", now=T0)
    conn = db.connect(work / "catalog.sqlite")
    set_suspended(conn, out, True, notice="Paused.")
    conn.close()
    restore_backup(backup, work, out, now=T0)
    assert read_manifest(out)["suspended"] is True and read_manifest(out)["version"] == "v2"


def test_restoring_never_replaces_a_version_folder_that_is_already_served(site, tmp_path):
    work, out = site
    backup = make_backup(work, out, tmp_path / "backups", now=T0)
    marker = out / "v1" / "marker.txt"
    marker.write_text("current")
    summary = restore_backup(backup, work, out, now=T0)
    assert marker.read_text() == "current" and "v1" in summary.skipped


def test_staging_stays_outside_the_served_folder(site, tmp_path, monkeypatch):
    work, out = site
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    shutil.rmtree(out)
    out.mkdir()
    seen: list[Path] = []
    real = backup_module._copy_version

    def spy(source, target):
        seen.append(source)
        assert not [p for p in out.iterdir() if p.name.startswith(".")], "dot-folder in served tree"
        real(source, target)

    monkeypatch.setattr(backup_module, "_copy_version", spy)
    restore_backup(path, work, out, now=T0)
    assert seen and all(work in s.parents for s in seen)
    assert not [p for p in out.iterdir() if p.name.startswith(".")] and not list(
        work.glob("restore-*")
    )


def test_backups_are_private_and_restored_files_stay_readable_by_the_web_server(site, tmp_path):
    work, out = site
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    assert path.stat().st_mode & 0o077 == 0
    assert all(f.stat().st_mode & 0o077 == 0 for f in path.iterdir())
    shutil.rmtree(out)
    out.mkdir()
    summary = restore_backup(path, work, out, now=T0)
    assert (out / "v1" / "reyna.json").stat().st_mode & 0o044 == 0o044
    assert (out / "manifest.json").stat().st_mode & 0o044 == 0o044
    shutil.rmtree(work / "before-restore-x", ignore_errors=True)
    assert summary.versions == ("v1", "v2")


def test_what_restore_keeps_aside_is_private(site, tmp_path):
    work, out = site
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    summary = restore_backup(path, work, out, now=T0)
    aside = summary.kept_aside
    assert aside is not None and aside.stat().st_mode & 0o077 == 0
    assert all(f.stat().st_mode & 0o077 == 0 for f in aside.rglob("*") if f.is_file())


def test_an_oversized_archive_is_refused_before_anything_is_written(site, tmp_path, monkeypatch):
    work, out = site
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    monkeypatch.setattr(backup_module, "MAX_EXTRACT_BYTES", 10)
    before = tree(out)
    with pytest.raises(BackupError, match="too large"):
        restore_backup(path, work, out, now=T0)
    assert tree(out) == before


def test_a_symlink_in_the_published_folder_does_not_break_backups(site, tmp_path):
    work, out = site
    (out / "latest").symlink_to(out / "v2")
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    with tarfile.open(path / "publish.tar.gz") as archive:
        assert "latest" not in archive.getnames()
    shutil.rmtree(out)
    out.mkdir()
    restore_backup(path, work, out, now=T0)


def test_backup_folder_names_must_be_plain_ascii_timestamps(tmp_path):
    (tmp_path / "kantahan-20261101T030000Z").mkdir()
    (tmp_path / "kantahan-\u0662\u0660\u0662\u0666\u0661\u0661\u0660\u0661T030000Z").mkdir()
    (tmp_path / "kantahan-20261101T030000Z\n").mkdir()
    assert [p.name for p in list_backups(tmp_path)] == ["kantahan-20261101T030000Z"]


def test_a_backup_whose_manifest_does_not_match_its_bundles_is_refused_on_a_bare_server(
    site, tmp_path
):
    work, out = site
    (out / "v2" / "reyna.json").write_bytes(b'{"schema":1}')  # damaged before it was backed up
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    shutil.rmtree(out)
    out.mkdir()
    with pytest.raises(BackupError, match="does not match"):
        restore_backup(path, work, out, now=T0)
    assert not (out / "manifest.json").exists()


def test_a_bare_server_gets_the_saved_manifest_back_byte_for_byte(site, tmp_path):
    work, out = site
    raw = (out / "manifest.json").read_bytes()
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    shutil.rmtree(out)
    out.mkdir()
    restore_backup(path, work, out, now=T0)
    assert (out / "manifest.json").read_bytes() == raw
