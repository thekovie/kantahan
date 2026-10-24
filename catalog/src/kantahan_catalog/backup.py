"""Backups of what a server cannot rebuild quickly: the database and the published catalog.

A backup is a private folder `kantahan-<UTC time>/` holding a consistent copy of the database (made
with SQLite's online backup, so it is safe while a run is writing), a tar of the published folder,
and SHA-256 sums of both. Downloaded PDFs are not included: they can be fetched again.

Restoring must never undo a takedown. Before anything is replaced it reads the takedown state of the
live system (withdrawn releases, the event log, how far publication numbers have gone, the live
manifest and its pause) and carries it into the restored database. It then refuses to bring back
any version folder at or below the withdrawal floor or the live version (those can still contain
withdrawn songs), never replaces a folder that is already served, and keeps the live manifest, with
its pause, when there is one. Everything is staged under `<work>/`, never in the served folder; what
it replaces is kept in `<work>/before-restore-<time>/`; files are private (0600) except the restored
catalog, which the web server must be able to read.
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
from typing import Any

from .publish import (
    PublishError,
    _manifest_lock,
    _withdrawn_floor,
    _write_atomic,
    check_bundle,
    read_manifest,
)

DB_NAME = "catalog.sqlite"
ARCHIVE = "publish.tar.gz"
SUMS = "checksums.sha256"
NAME = re.compile(r"kantahan-[0-9]{8}T[0-9]{6}Z")
_VERSION_DIR = re.compile(r"v[0-9]+")
DEFAULT_KEEP = 14
CHUNK = 1024 * 1024
MAX_EXTRACT_BYTES = 8 * 1024**3  # a published catalog is a few megabytes per version
PRIVATE_DIR = 0o700
PRIVATE_FILE = 0o600


class BackupError(Exception):
    pass


@dataclass(frozen=True)
class RestoreSummary:
    live_version: str | None
    versions: tuple[str, ...]  # version folders brought back
    skipped: tuple[
        str, ...
    ]  # backup versions left out (may hold withdrawn songs, or already served)
    kept_aside: Path | None
    notes: tuple[str, ...] = ()


def _stamp(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _sync(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def list_backups(dest: Path) -> list[Path]:
    if not dest.is_dir():
        return []
    return sorted(p for p in dest.iterdir() if p.is_dir() and NAME.fullmatch(p.name))


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
    if info.issym() or info.islnk():  # restore refuses links, so never write one
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
    partial.mkdir(mode=PRIVATE_DIR)
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
        for f in (DB_NAME, ARCHIVE, SUMS):
            (partial / f).chmod(PRIVATE_FILE)
            _sync(partial / f)
        os.replace(partial, target)
        _sync(dest)
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
        total = 0
        for member in members:
            parts = Path(member.name).parts
            if (
                member.name.startswith("/")
                or ".." in parts
                or not (member.isreg() or member.isdir())
            ):
                raise BackupError(f"unsafe member {member.name!r} in the archive")
            total += member.size if member.isreg() else 0
        if total > MAX_EXTRACT_BYTES:
            raise BackupError("the archive is too large to restore")
        into.mkdir(parents=True, exist_ok=True)
        for member in members:
            archive.extract(member, into, filter="data")


def _copy_version(source: Path, target: Path) -> None:
    try:
        shutil.copytree(source, target)
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise


def _keep_aside(aside: Path, path: Path, relative: str) -> None:
    destination = aside / relative
    destination.parent.mkdir(parents=True, exist_ok=True, mode=PRIVATE_DIR)
    aside.chmod(PRIVATE_DIR)
    if path.is_dir():
        shutil.copytree(path, destination)
        for item in [destination, *destination.rglob("*")]:
            item.chmod(PRIVATE_DIR if item.is_dir() else PRIVATE_FILE)
    else:
        shutil.copy2(path, destination)
        destination.chmod(PRIVATE_FILE)


def _version_number(name: str) -> int:
    return int(name[1:])


def _live_takedowns(db_path: Path) -> dict[str, Any] | None:
    """What the live database knows about takedowns, or None when it cannot be read."""
    if not db_path.exists():
        return {"withdrawn": [], "events": [], "max_publication": 0}
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        withdrawn = conn.execute(
            "SELECT d.sha256, r.withdrawn_at FROM release r "
            "JOIN document d ON d.id = r.document_id WHERE r.withdrawn_at IS NOT NULL"
        ).fetchall()
        events = conn.execute(
            "SELECT at, action, version, detail FROM publication_event"
        ).fetchall()
        seq = conn.execute(
            "SELECT max(seq) FROM sqlite_sequence WHERE name = 'publication'"
        ).fetchone()
        top = conn.execute("SELECT max(id) FROM publication").fetchone()
        return {
            "withdrawn": [tuple(r) for r in withdrawn],
            "events": [tuple(r) for r in events],
            "max_publication": max(seq[0] or 0, top[0] or 0),
        }
    except sqlite3.DatabaseError:
        return None
    finally:
        conn.close()


def _carry_takedowns(staged_db: Path, state: dict[str, Any], at_least: int) -> None:
    conn = sqlite3.connect(staged_db)
    try:
        with conn:
            for sha, at in state["withdrawn"]:
                conn.execute(
                    "UPDATE release SET withdrawn_at = ? WHERE withdrawn_at IS NULL "
                    "AND document_id IN (SELECT id FROM document WHERE sha256 = ?)",
                    (at, sha),
                )
            have = {
                tuple(r)
                for r in conn.execute("SELECT at, action, version, detail FROM publication_event")
            }
            for event in state["events"]:
                if tuple(event) not in have:
                    conn.execute(
                        "INSERT INTO publication_event (at, action, version, detail) "
                        "VALUES (?, ?, ?, ?)",
                        event,
                    )
            top = max(state["max_publication"], at_least)
            row = conn.execute(
                "SELECT seq FROM sqlite_sequence WHERE name = 'publication'"
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO sqlite_sequence (name, seq) VALUES ('publication', ?)", (top,)
                )
            elif row[0] < top:
                conn.execute(
                    "UPDATE sqlite_sequence SET seq = ? WHERE name = 'publication'", (top,)
                )
    finally:
        conn.close()


def _check_manifest_files(manifest: dict[str, Any], folder: Path) -> None:
    """Every bundle the manifest names must exist and match its checksum and format."""
    version = str(manifest["version"])
    for model in manifest["models"]:
        path = folder / Path(model["file"]).name
        try:
            payload = path.read_bytes()
            ok = hashlib.sha256(payload).hexdigest() == model["sha256"]
            if ok:
                check_bundle(payload, model["slug"])
        except (OSError, PublishError):
            ok = False
        if not ok:
            raise BackupError(
                f"{version}/{model['slug']} does not match the manifest: refusing to restore it"
            )


def restore_backup(
    backup: Path, work: Path, publish_dir: Path, *, now: datetime | None = None
) -> RestoreSummary:
    _verify(backup)
    stamp = _stamp(now)
    publish_dir.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    staging = work / f"restore-{stamp}"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(mode=PRIVATE_DIR)
    try:
        return _restore(backup, work, publish_dir, staging, stamp)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _read_live_manifest(folder: Path) -> dict[str, Any] | None:
    try:
        return read_manifest(folder)
    except ValueError:
        return None


def _pick_manifest(staged: Path, restorable: list[str], bound: int) -> Path | None:
    """With nothing live: the backup's manifest if allowed back, else the newest version's."""
    backed_up = _read_live_manifest(staged)
    if backed_up is not None:
        version = str(backed_up["version"])
        if _version_number(version) > bound and version in restorable:
            return staged / "manifest.json"
    for name in reversed(restorable):
        if _read_live_manifest(staged / name) is not None:
            return staged / name / "manifest.json"
    return None


def _restore(
    backup: Path, work: Path, publish_dir: Path, staging: Path, stamp: str
) -> RestoreSummary:
    notes: list[str] = []
    staged = staging / "publish"
    _extract(backup / ARCHIVE, staged)

    live = _read_live_manifest(publish_dir)
    live_number = _version_number(str(live["version"])) if live else 0
    takedowns = _live_takedowns(work / DB_NAME)
    if takedowns is None:
        notes.append(
            "the current database could not be read, so takedowns made after this backup were not "
            "carried over; check them before publishing"
        )
        takedowns = {"withdrawn": [], "events": [], "max_publication": 0}

    staged_db = staging / DB_NAME
    shutil.copyfile(backup / DB_NAME, staged_db)
    staged_db.chmod(PRIVATE_FILE)
    _carry_takedowns(staged_db, takedowns, at_least=live_number)
    conn = sqlite3.connect(staged_db)
    try:
        floor = _withdrawn_floor(conn)
    finally:
        conn.close()
    if not _database_ok(staged_db):
        raise BackupError("the restored database failed its integrity check")

    bound = max(floor, live_number)  # these versions may hold songs that were withdrawn
    restorable: list[str] = []
    skipped: list[str] = []
    for name in sorted(
        (p.name for p in staged.iterdir() if p.is_dir() and _VERSION_DIR.fullmatch(p.name)),
        key=_version_number,
    ):
        if _version_number(name) <= bound or (publish_dir / name).exists():
            skipped.append(name)
        else:
            restorable.append(name)

    candidate_file = None if live else _pick_manifest(staged, restorable, bound)
    candidate_bytes = candidate_file.read_bytes() if candidate_file else None
    if candidate_file is not None:
        candidate = json.loads(candidate_bytes or b"{}")
        _check_manifest_files(candidate, staged / str(candidate["version"]))

    aside = work / f"before-restore-{stamp}"
    for name in restorable:
        _copy_version(staged / name, publish_dir / name)
    if candidate_bytes is not None:
        with _manifest_lock(publish_dir):  # the saved file, byte for byte
            _write_atomic(publish_dir / "manifest.json", candidate_bytes)
    current_db = work / DB_NAME
    kept = False
    if current_db.exists():
        _keep_aside(aside, current_db, DB_NAME)
        kept = True
    for leftover in (f"{DB_NAME}-journal", f"{DB_NAME}-wal", f"{DB_NAME}-shm"):
        (work / leftover).unlink(missing_ok=True)
    os.replace(staged_db, current_db)

    final = _read_live_manifest(publish_dir)
    return RestoreSummary(
        str(final["version"]) if final else None,
        tuple(restorable),
        tuple(skipped),
        aside if kept else None,
        tuple(notes),
    )
