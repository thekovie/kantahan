"""Backups of what a server cannot rebuild quickly: the database and the published catalog.

A backup is a folder `kantahan-<UTC time>/` holding a consistent copy of the database (made with
SQLite's online backup, so it is safe while a run is writing), a tar of the published folder, and
SHA-256 sums of both. Downloaded PDFs are not included: they can be fetched again.

Restoring checks the sums and the database first, refuses unsafe archive members, keeps whatever
it replaces in `<work>/before-restore-<time>/` (never inside the served folder), and swaps the
manifest in last, like a publish.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DB_NAME = "catalog.sqlite"
ARCHIVE = "publish.tar.gz"
SUMS = "checksums.sha256"
NAME = re.compile(r"^kantahan-\d{8}T\d{6}Z$")
_VERSION_DIR = re.compile(r"^v\d+$")
DEFAULT_KEEP = 14
CHUNK = 1024 * 1024


class BackupError(Exception):
    pass


@dataclass(frozen=True)
class RestoreSummary:
    live_version: str | None
    versions: tuple[str, ...]
    kept_aside: Path | None


def _stamp(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def list_backups(dest: Path) -> list[Path]:
    if not dest.is_dir():
        return []
    return sorted(p for p in dest.iterdir() if p.is_dir() and NAME.match(p.name))


def _database_ok(path: Path) -> bool:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return bool(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok")
    except sqlite3.DatabaseError:
        return False
    finally:
        conn.close()


def _archive_filter(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    parts = Path(info.name).parts
    if any(part.startswith(".staging") or part.endswith(".part") for part in parts):
        return None
    return info


def make_backup(
    work: Path,
    publish_dir: Path,
    dest: Path,
    *,
    keep: int = DEFAULT_KEEP,
    now: datetime | None = None,
) -> Path:
    source = work / DB_NAME
    if not source.exists():
        raise BackupError(f"no database at {source}")
    name = f"kantahan-{_stamp(now)}"
    target = dest / name
    if target.exists():
        raise BackupError(f"{target} already exists")
    dest.mkdir(parents=True, exist_ok=True)
    partial = dest / f".{name}.part"
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir()
    try:
        origin = sqlite3.connect(source)
        copy = sqlite3.connect(partial / DB_NAME)
        try:
            origin.backup(copy)
        finally:
            copy.close()
            origin.close()
        if not _database_ok(partial / DB_NAME):
            raise BackupError("the copied database failed its integrity check")
        with tarfile.open(partial / ARCHIVE, "w:gz") as archive:
            if publish_dir.is_dir():
                for entry in sorted(publish_dir.iterdir()):
                    archive.add(entry, arcname=entry.name, filter=_archive_filter)
        (partial / SUMS).write_text(
            "".join(f"{_sha256(partial / f)}  {f}\n" for f in (DB_NAME, ARCHIVE)), encoding="utf-8"
        )
        os.replace(partial, target)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    for old in list_backups(dest)[: max(len(list_backups(dest)) - max(keep, 1), 0)]:
        if old != target:
            shutil.rmtree(old)
    return target


def _read_sums(path: Path) -> dict[str, str]:
    sums: dict[str, str] = {}
    for line in path.read_text("utf-8").splitlines():
        digest, _, name = line.partition("  ")
        if digest and name.strip():
            sums[name.strip()] = digest.strip()
    return sums


def _verify(backup: Path) -> None:
    if not backup.is_dir() or not all((backup / f).exists() for f in (DB_NAME, ARCHIVE)):
        raise BackupError(f"{backup} is not a backup folder")
    sums_file = backup / SUMS
    if not sums_file.exists():
        raise BackupError("the checksum file is missing")
    sums = _read_sums(sums_file)
    for name in (DB_NAME, ARCHIVE):
        if not sums.get(name) or _sha256(backup / name) != sums[name]:
            raise BackupError(f"checksum mismatch for {name}: the backup is damaged")
    if not _database_ok(backup / DB_NAME):
        raise BackupError("the backed-up database failed its integrity check")


def _extract(archive_path: Path, into: Path) -> None:
    with tarfile.open(archive_path) as archive:
        members = archive.getmembers()
        for member in members:
            parts = Path(member.name).parts
            if (
                member.name.startswith("/")
                or ".." in parts
                or not (member.isreg() or member.isdir())
            ):
                raise BackupError(f"unsafe member {member.name!r} in the archive")
        into.mkdir(parents=True)
        for member in members:
            archive.extract(member, into, filter="data")


def _place(source: Path, target: Path) -> None:
    os.replace(source, target)


def restore_backup(
    backup: Path, work: Path, publish_dir: Path, *, now: datetime | None = None
) -> RestoreSummary:
    _verify(backup)
    stamp = _stamp(now)
    publish_dir.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    staging = publish_dir / f".restore-{stamp}"
    shutil.rmtree(staging, ignore_errors=True)
    try:
        _extract(backup / ARCHIVE, staging)
        aside = work / f"before-restore-{stamp}"
        kept = False

        def keep_aside(path: Path, relative: str) -> None:
            nonlocal kept
            destination = aside / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if path.is_dir():
                shutil.copytree(path, destination)
            else:
                shutil.copy2(path, destination)
            kept = True

        current_db = work / DB_NAME
        if current_db.exists():
            keep_aside(current_db, DB_NAME)
        restoring = work / f"{DB_NAME}.restoring"
        shutil.copyfile(backup / DB_NAME, restoring)
        os.replace(restoring, current_db)

        versions = sorted(
            (p.name for p in staging.iterdir() if p.is_dir() and _VERSION_DIR.match(p.name)),
            key=lambda n: int(n[1:]),
        )
        for name in versions:
            existing = publish_dir / name
            if existing.exists():
                keep_aside(existing, f"publish/{name}")
                shutil.rmtree(existing)
            _place(staging / name, existing)
        live = None
        manifest = staging / "manifest.json"
        if manifest.exists():
            current_manifest = publish_dir / "manifest.json"
            if current_manifest.exists():
                keep_aside(current_manifest, "publish/manifest.json")
            part = publish_dir / "manifest.json.part"
            shutil.copyfile(manifest, part)
            _place(part, current_manifest)
            live = str(json.loads(current_manifest.read_text("utf-8"))["version"])
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return RestoreSummary(live, tuple(versions), aside if kept else None)
