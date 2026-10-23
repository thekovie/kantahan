"""Import one downloaded document into the database.

Rules: identical bytes are never re-imported; a document with validation errors is
quarantined and contributes no rows; a release is tied to a model only through header
evidence (see classify.FAMILY_TO_MODEL), otherwise it is held and never built; a newer
document for the same file supersedes the older release.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .classify import FAMILY_TO_MODEL, classify_header
from .extract import extract_rows
from .models import DocumentExtract, ExtractionError, Issue
from .normalize import fold
from .validate import has_errors, validate_document

FILE_KEY = re.compile(r"mediafire\.com/file(?:_premium)?/(\w+)/")
MAX_QUARANTINE_SAMPLES = 50


@dataclass(frozen=True)
class ImportResult:
    outcome: str  # imported | unchanged | quarantined
    document_id: int
    release_id: int | None
    rows: int
    issues: tuple[Issue, ...]
    status: str | None  # mapped | held | None


def _stamp(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).isoformat(timespec="seconds")


def ensure_source(conn: sqlite3.Connection, slug: str, base_url: str, priority: str) -> int:
    conn.execute(
        "INSERT INTO source (slug, base_url, priority) VALUES (?, ?, ?) "
        "ON CONFLICT(slug) DO UPDATE SET "
        "base_url = excluded.base_url, priority = excluded.priority",
        (slug, base_url, priority),
    )
    conn.commit()
    return int(conn.execute("SELECT id FROM source WHERE slug = ?", (slug,)).fetchone()["id"])


def _touch_link(
    conn: sqlite3.Connection, source_id: int, document_id: int, url: str, label: str, stamp: str
) -> None:
    conn.execute(
        "INSERT INTO document_link (source_id, document_id, url, label, first_seen, last_seen) "
        "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(source_id, url) DO UPDATE SET "
        "document_id = excluded.document_id, label = excluded.label, "
        "last_seen = excluded.last_seen, removed_at = NULL",
        (source_id, document_id, url, label, stamp, stamp),
    )


def _earlier_releases(
    conn: sqlite3.Connection, source_id: int, url: str, file_key: str | None
) -> list[sqlite3.Row]:
    """Live releases for the same file, found by file key or by what the link pointed at.

    Looking at the file key keeps the baseline after a quarantined re-download repoints the link.
    """
    return conn.execute(
        "SELECT r.id, (SELECT count(*) FROM song_entry WHERE release_id = r.id) AS n "
        "FROM release r JOIN document d ON d.id = r.document_id "
        "WHERE r.superseded_by IS NULL AND ("
        "  (? IS NOT NULL AND d.file_key = ?) OR r.document_id IN "
        "  (SELECT document_id FROM document_link WHERE source_id = ? AND url = ?)) "
        "ORDER BY r.id DESC",
        (file_key, file_key, source_id, url),
    ).fetchall()


def _quarantine(
    conn: sqlite3.Connection, document_id: int, issues: list[Issue], stamp: str
) -> None:
    errors = [i for i in issues if i.severity == "error"]
    for code in dict.fromkeys(i.code for i in errors):
        same = [i for i in errors if i.code == code]
        details = {
            "count": len(same),
            "samples": [
                {"number": i.number, "message": i.message} for i in same[:MAX_QUARANTINE_SAMPLES]
            ],
        }
        conn.execute(
            "INSERT INTO quarantine (document_id, reason, details_json, created_at) "
            "VALUES (?, ?, ?, ?)",
            (document_id, code, json.dumps(details), stamp),
        )


def _insert_entries(conn: sqlite3.Connection, release_id: int, extract: DocumentExtract) -> None:
    seen: set[str] = set()
    for r in extract.rows:
        if r.number in seen:
            continue  # identical re-listing inside one document (conflicts never get here)
        seen.add(r.number)
        uncertain = "overprint" in r.flags
        title_norm = fold(r.title)
        artist_norm = "" if uncertain else fold(r.artist)
        song_id = None
        if title_norm and artist_norm and "title_overprint" not in r.flags:
            conn.execute(
                "INSERT OR IGNORE INTO song (title_norm, artist_norm) VALUES (?, ?)",
                (title_norm, artist_norm),
            )
            song_id = conn.execute(
                "SELECT id FROM song WHERE title_norm = ? AND artist_norm = ?",
                (title_norm, artist_norm),
            ).fetchone()["id"]
        conn.execute(
            "INSERT INTO song_entry (release_id, song_id, number, title_raw, artist_raw, "
            "title_norm, artist_norm, page, flags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                release_id,
                song_id,
                r.number,
                r.title,
                r.artist,
                title_norm,
                artist_norm,
                r.page,
                ",".join(r.flags),
            ),
        )


def _forget_quarantined(conn: sqlite3.Connection, document_id: int) -> None:
    """Drop a document, its release and songs, so it is evaluated again after an extractor fix."""
    with conn:
        conn.execute(
            "UPDATE document_link SET document_id = NULL WHERE document_id = ?", (document_id,)
        )
        conn.execute("DELETE FROM document WHERE id = ?", (document_id,))


def import_pdf(
    conn: sqlite3.Connection,
    path: str | Path,
    *,
    source_slug: str,
    url: str,
    label: str,
    now: datetime | None = None,
    retry_quarantined: bool = False,
    reimport: bool = False,
    blank_artists_ok: bool = False,
) -> ImportResult:
    stamp = _stamp(now)
    data = Path(path).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    source = conn.execute("SELECT id FROM source WHERE slug = ?", (source_slug,)).fetchone()
    if source is None:
        raise KeyError(f"unknown source {source_slug!r}; call ensure_source first")
    source_id = int(source["id"])

    existing = conn.execute("SELECT id, status FROM document WHERE sha256 = ?", (sha,)).fetchone()
    if existing and (reimport or (retry_quarantined and existing["status"] == "quarantined")):
        _forget_quarantined(conn, existing["id"])
        existing = None
    if existing:
        return _unchanged(conn, existing, source_id, url, label, stamp)

    key_match = FILE_KEY.search(url)
    file_key = key_match.group(1) if key_match else None
    earlier = _earlier_releases(conn, source_id, url, file_key)
    previous = earlier[0]["n"] if earlier else None
    extract: DocumentExtract | None
    try:
        extract = extract_rows(path)
        issues = validate_document(extract, previous or None, blank_artists_ok)
    except ExtractionError as exc:
        extract, issues = None, [Issue("extraction_failed", "error", str(exc))]
    blocked = has_errors(issues)
    classification = classify_header(extract.header_lines) if extract else None

    with conn:
        document_id = conn.execute(
            "INSERT INTO document (sha256, bytes, pages, file_key, header_text, header_family, "
            "header_evidence, status, first_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                sha,
                len(data),
                extract.pages if extract else None,
                file_key,
                "\n".join(extract.header_lines) if extract else None,
                classification.family if classification else None,
                classification.evidence if classification else None,
                "quarantined" if blocked else "ok",
                stamp,
            ),
        ).lastrowid
        assert document_id is not None
        _touch_link(conn, source_id, document_id, url, label, stamp)
        if blocked or extract is None or classification is None:
            _quarantine(conn, document_id, issues, stamp)
            return ImportResult("quarantined", document_id, None, 0, tuple(issues), None)
        status = "mapped" if classification.family in FAMILY_TO_MODEL else "held"
        release_id = conn.execute(
            "INSERT INTO release (document_id, label, status) VALUES (?, ?, ?)",
            (document_id, label, status),
        ).lastrowid
        assert release_id is not None
        for old in earlier:
            conn.execute(
                "UPDATE release SET superseded_by = ? WHERE id = ?", (release_id, old["id"])
            )
        if status == "mapped":
            conn.execute(
                "INSERT INTO release_model (release_id, model_id, evidence) "
                "SELECT ?, id, ? FROM model WHERE slug = ?",
                (
                    release_id,
                    f"page-1 header: {classification.evidence}",
                    FAMILY_TO_MODEL[classification.family],
                ),
            )
        _insert_entries(conn, release_id, extract)
    return ImportResult(
        "imported", document_id, release_id, len(extract.rows), tuple(issues), status
    )


def _unchanged(
    conn: sqlite3.Connection,
    existing: sqlite3.Row,
    source_id: int,
    url: str,
    label: str,
    stamp: str,
) -> ImportResult:
    with conn:
        _touch_link(conn, source_id, existing["id"], url, label, stamp)
    release = conn.execute(
        "SELECT r.id, r.status, (SELECT count(*) FROM song_entry WHERE release_id = r.id) AS n "
        "FROM release r WHERE r.document_id = ?",
        (existing["id"],),
    ).fetchone()
    return ImportResult(
        "unchanged",
        existing["id"],
        release["id"] if release else None,
        release["n"] if release else 0,
        (),
        release["status"] if release else None,
    )
