"""Build a per-model catalog bundle from the database (local output only, never committed).

Only live (not superseded) releases mapped to the model through header evidence are used.
Numbers that two releases list with a different title are conflicts: they are left out, and the
build is validated only when they are no more than `max_conflict_share` of the model's numbers
(default none). A number whose title agrees but whose artist text differs keeps the song and
withholds the artist. Rows with uncertain artist text keep number and title but have
the artist withheld; rows with uncertain title text are left out.

Every build is written to an immutable `<model>.v<version>.json`. The stable `<model>.json`
is replaced (atomically) only by a validated build, so a partial build never overwrites it.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = 1


class BuildError(Exception):
    pass


@dataclass(frozen=True)
class BuildResult:
    version_id: int
    status: str  # validated | building (conflicts present)
    path: Path  # the stable file when validated, otherwise the versioned file
    sha256: str
    songs: int
    artists_withheld: int
    titles_excluded: int
    conflicts: tuple[str, ...]


_LIVE_MAPPED = (
    "FROM song_entry se JOIN release r ON r.id = se.release_id "
    "JOIN release_model rm ON rm.release_id = r.id "
    "JOIN model m ON m.id = rm.model_id "
    "WHERE m.slug = ? AND r.status = 'mapped' AND r.superseded_by IS NULL "
    "AND r.withdrawn_at IS NULL"
)


def _entries(conn: sqlite3.Connection, model_slug: str) -> tuple[list[sqlite3.Row], int]:
    rows = conn.execute(
        "SELECT se.number, se.title_raw, se.artist_raw, se.title_norm, se.artist_norm, se.flags, "
        f"r.id AS release_id, r.label {_LIVE_MAPPED} ORDER BY r.id, se.number",
        (model_slug,),
    ).fetchall()
    usable = [e for e in rows if "title_overprint" not in e["flags"].split(",")]
    return usable, len(rows) - len(usable)


def _merge(entries: list[sqlite3.Row]) -> tuple[list[sqlite3.Row], list[str], set[str]]:
    """One entry per number. Identical re-listings collapse. Returns (kept, conflicts, artist_open).

    A different title for one number is a conflict. The same title with different artist text
    keeps the song, and its number is returned in `artist_open` so the artist is withheld.
    """
    by_number: dict[str, list[sqlite3.Row]] = {}
    for e in entries:
        by_number.setdefault(e["number"], []).append(e)
    kept: list[sqlite3.Row] = []
    conflicts: list[str] = []
    artist_open: set[str] = set()
    for number in sorted(by_number):
        group = by_number[number]
        if len({g["title_norm"] for g in group}) > 1:
            conflicts.append(number)
            continue
        if len({g["artist_norm"] for g in group}) > 1:
            artist_open.add(number)
        kept.append(group[0])
    return kept, conflicts, artist_open


def _write_atomic(path: Path, payload: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(payload)
    os.replace(tmp, path)


def _payload(model_slug: str, kept: list[sqlite3.Row], artist_open: set[str]) -> bytes:
    labels: list[str] = []
    for e in kept:
        if e["label"] not in labels:
            labels.append(e["label"])
    withheld = ["overprint" in e["flags"].split(",") or e["number"] in artist_open for e in kept]
    bundle = {
        "schema": SCHEMA,
        "model": model_slug,
        "count": len(kept),
        "releases": labels,
        "n": [e["number"] for e in kept],
        "t": [e["title_raw"] for e in kept],
        "a": ["" if w else e["artist_raw"] for e, w in zip(kept, withheld, strict=True)],
        "r": [labels.index(e["label"]) for e in kept],
        "u": [1 if w else 0 for w in withheld],
    }
    return json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def build_bundle(
    conn: sqlite3.Connection,
    model_slug: str,
    out_dir: str | Path,
    now: datetime | None = None,
    max_conflict_share: float = 0.0,
) -> BuildResult:
    model = conn.execute("SELECT id FROM model WHERE slug = ?", (model_slug,)).fetchone()
    if model is None:
        raise BuildError(f"unknown model {model_slug!r}")
    entries, titles_excluded = _entries(conn, model_slug)
    kept, conflicts, artist_open = _merge(entries)
    if not entries:
        raise BuildError(f"no mapped releases with songs for model {model_slug!r}")
    if not kept:
        raise BuildError(
            f"every number conflicts between releases ({len(conflicts)}); nothing to build"
        )

    payload = _payload(model_slug, kept, artist_open)
    digest = hashlib.sha256(payload).hexdigest()
    share = len(conflicts) / (len(kept) + len(conflicts))
    status = "validated" if share <= max_conflict_share else "building"
    stamp = (now or datetime.now(UTC)).isoformat(timespec="seconds")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    with conn:
        parent = conn.execute("SELECT max(id) AS id FROM catalog_version").fetchone()["id"]
        version_id = conn.execute(
            "INSERT INTO catalog_version (created_at, status, parent_id, notes) "
            "VALUES (?, ?, ?, ?)",
            (
                stamp,
                status,
                parent,
                json.dumps({"conflicts": len(conflicts), "titles_excluded": titles_excluded}),
            ),
        ).lastrowid
        assert version_id is not None
        conn.execute(
            "INSERT INTO catalog_version_model (version_id, model_id, bundle_sha256, song_count) "
            "VALUES (?, ?, ?, ?)",
            (version_id, model["id"], digest, len(kept)),
        )
        path = out / f"{model_slug}.v{version_id}.json"
        _write_atomic(path, payload)
        if status == "validated":
            path = out / f"{model_slug}.json"
            _write_atomic(path, payload)
    withheld = sum(
        1 for e in kept if "overprint" in e["flags"].split(",") or e["number"] in artist_open
    )
    return BuildResult(
        version_id, status, path, digest, len(kept), withheld, titles_excluded, tuple(conflicts)
    )
