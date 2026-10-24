"""Scheduled-run plumbing: one run at a time, a "due" check, run records, and the audit.

The scheduler is the host's cron, which starts `kantahan-catalog run` daily; the run itself
decides whether a pass is due (default every 14 days) so a failed run is retried the next day.
"""

from __future__ import annotations

import fcntl
import json
import shutil
import sqlite3
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .discover import DiscoveredLink
from .fetch import Fetcher, FetchError

SUCCESS = ("published", "unchanged")


class RunLocked(Exception):
    pass


@contextmanager
def run_lock(work: Path) -> Iterator[None]:
    """Hold an exclusive lock for the whole run; a second run fails fast instead of waiting."""
    work.mkdir(parents=True, exist_ok=True)
    with (work / "run.lock").open("w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RunLocked("another catalog run is in progress") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def free_bytes(path: Path) -> int:
    """Free space on the volume holding `path` (or the nearest folder above it that exists)."""
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return shutil.disk_usage(probe).free


def _stamp(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).isoformat(timespec="seconds")


def start_run(conn: sqlite3.Connection, kind: str, now: datetime | None = None) -> int:
    with conn:
        run_id = conn.execute(
            "INSERT INTO import_run (kind, started_at) VALUES (?, ?)", (kind, _stamp(now))
        ).lastrowid
    assert run_id is not None
    return run_id


def finish_run(
    conn: sqlite3.Connection,
    run_id: int,
    outcome: str,
    stats: dict[str, object],
    now: datetime | None = None,
) -> None:
    with conn:
        conn.execute(
            "UPDATE import_run SET finished_at = ?, outcome = ?, stats_json = ? WHERE id = ?",
            (_stamp(now), outcome, json.dumps(stats, sort_keys=True), run_id),
        )


def is_due(conn: sqlite3.Connection, days: int, now: datetime | None = None) -> bool:
    """True when no scheduled run succeeded within the last `days` days."""
    row = conn.execute(
        "SELECT max(finished_at) FROM import_run WHERE kind = 'scheduled' "
        f"AND outcome IN ({','.join('?' * len(SUCCESS))})",
        SUCCESS,
    ).fetchone()
    if row[0] is None:
        return True
    return (now or datetime.now(UTC)) - datetime.fromisoformat(row[0]) >= timedelta(days=days)


@dataclass(frozen=True)
class AuditResult:
    checked: int
    changed: tuple[str, ...]
    failed: tuple[str, ...]
    new: int


def audit_links(
    conn: sqlite3.Connection, fetcher: Fetcher, links: Sequence[DiscoveredLink]
) -> AuditResult:
    """Download every known document again and compare its hash with what was imported.

    The document host sends no ETag or Last-Modified, so a file replaced behind the same link
    is only visible by hashing it. Nothing is imported here: drift is reported for a human.
    """
    changed: list[str] = []
    failed: list[str] = []
    new = checked = 0
    with tempfile.TemporaryDirectory(prefix="kantahan-audit-") as scratch:
        for link in links:
            known = conn.execute(
                "SELECT d.sha256 FROM document_link l JOIN document d ON d.id = l.document_id "
                "JOIN source s ON s.id = l.source_id WHERE s.slug = ? AND l.url = ?",
                (link.source, link.url),
            ).fetchone()
            if known is None:
                new += 1
                continue
            try:
                digest, _ = fetcher.download_pdf(link.url, Path(scratch) / "doc.pdf")
            except FetchError:
                failed.append(link.label)
                continue
            checked += 1
            if digest != known[0]:
                changed.append(link.label)
    return AuditResult(checked, tuple(changed), tuple(failed), new)
