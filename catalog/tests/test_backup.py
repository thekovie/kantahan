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
from kantahan_catalog.publish import publish, read_manifest

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


def test_the_manifest_is_swapped_in_last(site, tmp_path, monkeypatch):
    work, out = site
    path = make_backup(work, out, tmp_path / "backups", now=T0)
    shutil.rmtree(out)
    out.mkdir()
    order: list[str] = []
    real = backup_module._place

    def spy(source, target):
        order.append(target.name)
        real(source, target)

    monkeypatch.setattr(backup_module, "_place", spy)
    restore_backup(path, work, out, now=T0)
    assert order[-1] == "manifest.json" and set(order[:-1]) == {"v1", "v2"}
