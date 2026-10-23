"""Publish validated bundles as immutable versions plus a manifest the app reads.

Layout under the publish folder (what a static host serves):

    manifest.json          the live catalog; replaced atomically, always the last step
    v<N>/<model>.json      immutable bundles of publication N (newest few and the live one kept)
    v<N>/manifest.json     the manifest as published, used by rollback

A publication is built in a staging folder, verified by re-reading it, and only then moved
into place and announced by swapping the manifest. Any failure leaves the live manifest
untouched. Bundles are plain JSON: the web server compresses them in transit, and the manifest
carries the SHA-256 of the exact bytes so the app can verify what it downloaded.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
import sqlite3
from collections.abc import Collection, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .build import BuildError, build_bundle

SCHEMA = 1
MANIFEST = "manifest.json"
HUES = ("magenta", "violet", "aqua", "orange", "lime", "yellow")
DEFAULT_KEEP = 5
MAX_TEXT = 80  # names and families shown on chips
MAX_NOTICE = 500
DEFAULT_MAX_DROP = 0.02  # a model may lose at most this share of its songs without --allow-drop
_VERSION = re.compile(r"v(\d+)")
_SLUG = re.compile(r"^[a-z0-9-]+$")
_DIGITS = re.compile(r"^\d+$")


class PublishError(Exception):
    """Publishing stopped. `blocked` means a safety gate refused; the live catalog is unchanged."""

    def __init__(self, message: str, blocked: bool = False) -> None:
        super().__init__(message)
        self.blocked = blocked


@dataclass(frozen=True)
class ModelDisplay:
    name: str
    family: str
    hue: str


@dataclass(frozen=True)
class Display:
    source_label: str
    source_url: str
    models: dict[str, ModelDisplay]


@dataclass(frozen=True)
class PublishResult:
    outcome: str  # published | unchanged
    version: str
    songs: dict[str, int]
    skipped: tuple[str, ...] = ()


def load_display(path: str | Path) -> Display:
    """Read display.yaml: how each published model is named and coloured in the app."""
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        source = data["source"]
        raw_models = data["models"]
        source_label, source_url = str(source["label"]), str(source["url"])
    except (OSError, KeyError, TypeError, yaml.YAMLError) as exc:
        raise PublishError(f"cannot read display file {path}: {exc}") from exc
    if not isinstance(raw_models, dict) or not isinstance(source, dict):
        raise PublishError("display file: 'source' and 'models' must be mappings")
    if not str(source.get("url", "")).startswith("https://"):
        raise PublishError("display file: source url must start with https://")
    models: dict[str, ModelDisplay] = {}
    for slug, entry in raw_models.items():
        if not isinstance(entry, dict):
            raise PublishError(f"model {slug}: entry must be a mapping")
        if not _SLUG.match(str(slug)):
            raise PublishError(f"model slug {slug!r} must be lowercase letters, digits and hyphens")
        if entry.get("hue") not in HUES:
            raise PublishError(f"model {slug}: hue must be one of {', '.join(HUES)}")
        for field in ("name", "family"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT:
                raise PublishError(
                    f"model {slug}: {field} is required (at most {MAX_TEXT} characters)"
                )
        models[slug] = ModelDisplay(entry["name"], entry["family"], entry["hue"])
    if not models:
        raise PublishError("display file lists no models")
    return Display(source_label, source_url, models)


def _stamp(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).isoformat(timespec="seconds")


def _canonical(manifest: dict[str, Any]) -> bytes:
    return (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _write_atomic(path: Path, payload: bytes) -> None:
    """Write beside the target, flush to disk, then rename: readers see the old or the new file."""
    tmp = path.with_name(path.name + ".part")
    with tmp.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


@contextmanager
def _manifest_lock(out: Path) -> Iterator[None]:
    """Short lock around reading and replacing manifest.json (held on the folder itself).

    Publish, rollback, suspend and resume all rewrite the manifest from what is there now, so
    they take turns; this is what lets `suspend` work while a long `run` is still fetching.
    """
    fd = os.open(out, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _swap_manifest(out_dir: Path, manifest: dict[str, Any]) -> bytes:
    payload = _canonical(manifest)
    _write_atomic(out_dir / MANIFEST, payload)
    return payload


def read_manifest(out_dir: str | Path) -> dict[str, Any] | None:
    path = Path(out_dir) / MANIFEST
    if not path.exists():
        return None
    result: dict[str, Any] = json.loads(path.read_text("utf-8"))
    return result


def _coverage(labels: list[str]) -> str:
    numbers = [int(n) for label in labels for n in re.findall(r"\d+", label)]
    if not numbers:
        return "Volumes not stated"
    low, high = min(numbers), max(numbers)
    return f"Volume {low}" if low == high else f"Volumes {low} to {high}"


def check_bundle(payload: bytes, slug: str) -> dict[str, Any]:
    """Re-read a bundle the way the app will and refuse anything malformed."""
    try:
        bundle = json.loads(payload)
    except ValueError as exc:
        raise PublishError(f"{slug}: bundle is not valid JSON") from exc
    columns = [bundle.get(k) for k in ("n", "t", "a", "r", "u")]
    if bundle.get("schema") != SCHEMA or bundle.get("model") != slug:
        raise PublishError(f"{slug}: bundle schema or model does not match")
    if not all(isinstance(c, list) for c in columns) or len({len(c) for c in columns}) != 1:
        raise PublishError(f"{slug}: bundle columns are missing or different lengths")
    if bundle.get("count") != len(columns[0]) or not columns[0]:
        raise PublishError(f"{slug}: bundle count does not match its rows")
    if not all(isinstance(n, str) and _DIGITS.match(n) for n in columns[0]):
        raise PublishError(f"{slug}: a song number is not digits")
    if len(set(columns[0])) != len(columns[0]):
        raise PublishError(f"{slug}: a song number appears twice")
    result: dict[str, Any] = bundle
    return result


def _live_version(out_dir: Path) -> str | None:
    manifest = read_manifest(out_dir)
    return str(manifest["version"]) if manifest else None


def _prune(out_dir: Path, keep: int) -> None:
    versions = sorted(
        (int(m[1]), p)
        for p in out_dir.iterdir()
        if p.is_dir() and (m := _VERSION.fullmatch(p.name))
    )
    live = _live_version(out_dir)
    for _, path in versions[: max(len(versions) - keep, 0)]:
        if path.name != live:
            shutil.rmtree(path)


def _purge_withdrawn(conn: sqlite3.Connection, out: Path) -> None:
    """Delete every version that still holds a withdrawn release, except the live one."""
    floor, live = _withdrawn_floor(conn), _live_version(out)
    for path in out.iterdir():
        match = _VERSION.fullmatch(path.name)
        if path.is_dir() and match and int(match[1]) <= floor and path.name != live:
            shutil.rmtree(path)


def _gate(
    previous: dict[str, Any] | None,
    songs: dict[str, int],
    max_drop: float,
    allow_drop: bool | Collection[str],
) -> None:
    if previous is None or allow_drop is True:
        return
    problems = []
    for model in previous["models"]:
        slug, before = model["slug"], int(model["songs"])
        if not isinstance(allow_drop, bool) and slug in allow_drop:
            continue
        if slug not in songs:
            problems.append(f"{slug} would disappear from the catalog")
        elif songs[slug] < before * (1 - max_drop):
            problems.append(f"{slug} dropped from {before} to {songs[slug]} songs")
    if problems:
        raise PublishError(
            "refusing to publish: " + "; ".join(problems) + " (use --allow-drop if intended)",
            blocked=True,
        )


def publish(
    conn: sqlite3.Connection,
    out_dir: str | Path,
    display: Display,
    *,
    keep: int = DEFAULT_KEEP,
    max_drop: float = DEFAULT_MAX_DROP,
    allow_drop: bool | Collection[str] = False,
    now: datetime | None = None,
) -> PublishResult:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    previous = read_manifest(out)
    for leftover in out.glob(".staging-*"):  # a crashed run; the folder is served, so remove it
        shutil.rmtree(leftover, ignore_errors=True)
    staging = out / f".staging-{os.getpid()}"
    staging.mkdir()
    try:
        return _publish(conn, out, staging, display, previous, keep, max_drop, allow_drop, now)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _build_all(
    conn: sqlite3.Connection, staging: Path, display: Display
) -> tuple[dict[str, bytes], list[str]]:
    payloads: dict[str, bytes] = {}
    skipped: list[str] = []
    conflicts: list[str] = []
    for slug in display.models:
        try:
            result = build_bundle(conn, slug, staging)
        except BuildError as exc:
            skipped.append(f"{slug}: {exc}")
            continue
        if result.status != "validated":
            conflicts.append(f"{slug}: {len(result.conflicts)} conflicting numbers")
            continue
        payloads[slug] = (staging / f"{slug}.json").read_bytes()
    if conflicts:
        raise PublishError("refusing to publish, " + "; ".join(conflicts), blocked=True)
    if not payloads:
        raise PublishError("nothing to publish: " + ("; ".join(skipped) or "no models"))
    return payloads, skipped


def _publish(
    conn: sqlite3.Connection,
    out: Path,
    staging: Path,
    display: Display,
    previous: dict[str, Any] | None,
    keep: int,
    max_drop: float,
    allow_drop: bool | Collection[str],
    now: datetime | None,
) -> PublishResult:
    payloads, skipped = _build_all(conn, staging, display)
    bundles = {slug: check_bundle(p, slug) for slug, p in payloads.items()}
    songs = {slug: int(b["count"]) for slug, b in bundles.items()}
    _gate(previous, songs, max_drop, allow_drop)

    digests = {slug: hashlib.sha256(p).hexdigest() for slug, p in payloads.items()}
    shown = {
        slug: (
            digests[slug],
            display.models[slug].name,
            display.models[slug].family,
            display.models[slug].hue,
            _coverage(bundles[slug]["releases"]),
        )
        for slug in payloads
    }
    if (
        previous
        and {
            m["slug"]: (m["sha256"], m["name"], m["family"], m["hue"], m["coverage"])
            for m in previous["models"]
        }
        == shown
    ):
        return PublishResult("unchanged", str(previous["version"]), songs, tuple(skipped))

    with conn:
        pub_id = conn.execute(
            "INSERT INTO publication (created_at, status) VALUES (?, 'building')", (_stamp(now),)
        ).lastrowid
    version = f"v{pub_id}"
    target = out / version
    if (
        target.exists()
    ):  # ids restart after restoring an old database; never touch a published folder
        with conn:
            conn.execute("UPDATE publication SET status = 'failed' WHERE id = ?", (pub_id,))
        raise PublishError(
            f"{version} already exists in {out}; the database may have been restored from an "
            "older backup. Move the folder away or publish from the current database.",
            blocked=True,
        )
    moved = False
    try:
        for slug, payload in payloads.items():
            (staging / f"{slug}.json").write_bytes(payload)
        for stray in staging.glob("*.v*.json"):
            stray.unlink()
        manifest: dict[str, Any] = {
            "schema": SCHEMA,
            "version": version,
            "generatedAt": _stamp(now),
            "synthetic": False,
            "suspended": bool(previous and previous.get("suspended")),
            "source": {"label": display.source_label, "url": display.source_url},
            "models": [
                {
                    "slug": slug,
                    "name": display.models[slug].name,
                    "family": display.models[slug].family,
                    "hue": display.models[slug].hue,
                    "file": f"{version}/{slug}.json",
                    "sha256": digests[slug],
                    "bytes": len(payloads[slug]),
                    "songs": songs[slug],
                    "coverage": _coverage(bundles[slug]["releases"]),
                }
                for slug in payloads
            ],
        }
        if previous and previous.get("notice"):
            manifest["notice"] = previous["notice"]
        (staging / MANIFEST).write_bytes(_canonical(manifest))
        for slug in payloads:  # self-check: what is on disk is what the manifest promises
            on_disk = (staging / f"{slug}.json").read_bytes()
            if hashlib.sha256(on_disk).hexdigest() != digests[slug]:
                raise PublishError(f"{slug}: written bundle does not match its hash")
        os.replace(staging, target)
        moved = True
        with _manifest_lock(out):  # carry over a pause that was set while this publish ran
            current = read_manifest(out)
            manifest["suspended"] = bool(current and current.get("suspended"))
            manifest.pop("notice", None)
            if current and current.get("notice"):
                manifest["notice"] = current["notice"]
            (target / MANIFEST).write_bytes(_canonical(manifest))
            raw = _swap_manifest(out, manifest)
    except Exception:
        if moved:
            shutil.rmtree(target, ignore_errors=True)
        with conn:
            conn.execute("UPDATE publication SET status = 'failed' WHERE id = ?", (pub_id,))
        raise
    with conn:
        conn.execute(
            "UPDATE publication SET status = 'published', manifest_sha256 = ? WHERE id = ?",
            (hashlib.sha256(raw).hexdigest(), pub_id),
        )
        conn.execute("UPDATE catalog_version SET status = 'published' WHERE status = 'validated'")
    _prune(out, keep)
    _purge_withdrawn(conn, out)
    return PublishResult("published", version, songs, tuple(skipped))


def _log(
    conn: sqlite3.Connection, action: str, version: str | None, detail: str, now: datetime | None
) -> None:
    with conn:
        conn.execute(
            "INSERT INTO publication_event (at, action, version, detail) VALUES (?, ?, ?, ?)",
            (_stamp(now), action, version, detail),
        )


def _withdrawn_floor(conn: sqlite3.Connection) -> int:
    """Highest version number published before the latest withdrawal (0 when none)."""
    rows = conn.execute(
        "SELECT version FROM publication_event WHERE action = 'withdraw'"
    ).fetchall()
    return max((int(r[0][1:]) for r in rows if r[0]), default=0)


def rollback(
    conn: sqlite3.Connection, out_dir: str | Path, version: str, now: datetime | None = None
) -> None:
    """Point the live manifest at an older version after re-checking its files."""
    out = Path(out_dir)
    if not _VERSION.fullmatch(version):
        raise PublishError(f"{version!r} is not a version like v3")
    saved = out / version / MANIFEST
    if not saved.exists():
        raise PublishError(f"no such version {version} in {out}")
    floor = _withdrawn_floor(conn)
    if int(version[1:]) <= floor:
        raise PublishError(
            f"{version} still contains a release that was withdrawn (versions up to v{floor}); "
            "publish a new version instead",
            blocked=True,
        )
    manifest: dict[str, Any] = json.loads(saved.read_text("utf-8"))
    for model in manifest["models"]:
        path = (out / model["file"]).resolve()
        if not path.is_relative_to(out.resolve()):
            raise PublishError(f"{version}: a bundle path leaves the publish folder")
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != model["sha256"]:
            raise PublishError(f"{version}/{model['slug']}: hash does not match the manifest")
        check_bundle(payload, model["slug"])
    with _manifest_lock(out):
        current = read_manifest(out)
        manifest["suspended"] = bool(current and current.get("suspended"))
        manifest.pop("notice", None)
        if current and current.get("notice"):
            manifest["notice"] = current["notice"]
        _swap_manifest(out, manifest)
    _log(conn, "rollback", version, f"from {current['version'] if current else 'none'}", now)


def set_suspended(
    conn: sqlite3.Connection,
    out_dir: str | Path,
    suspended: bool,
    notice: str | None = None,
    now: datetime | None = None,
) -> None:
    """Hide (or show again) the catalog in every app that checks in, without touching bundles."""
    out = Path(out_dir)
    if not out.is_dir():
        raise PublishError(f"nothing is published in {out}")
    if notice and len(notice) > MAX_NOTICE:
        raise PublishError(f"notice is too long (at most {MAX_NOTICE} characters)")
    with _manifest_lock(out):
        manifest = read_manifest(out)
        if manifest is None:
            raise PublishError(f"nothing is published in {out}")
        manifest["suspended"] = suspended
        manifest.pop("notice", None)
        if suspended and notice:
            manifest["notice"] = notice
        _swap_manifest(out, manifest)
    _log(conn, "suspend" if suspended else "resume", str(manifest["version"]), notice or "", now)


def withdraw_release(
    conn: sqlite3.Connection,
    *,
    label: str | None = None,
    release_id: int | None = None,
    now: datetime | None = None,
) -> list[str]:
    """Leave one live release out of every later build. Returns the models it was built into."""
    if (label is None) == (release_id is None):
        raise PublishError("give either a release label or a release id")
    where, param = ("label = ?", label) if label is not None else ("id = ?", release_id)
    rows = conn.execute(
        f"SELECT id, label FROM release WHERE {where} AND withdrawn_at IS NULL", (param,)
    ).fetchall()
    if not rows:
        raise PublishError(f"no live release matches {param!r}")
    if len(rows) > 1:
        ids = ", ".join(f"#{r['id']}" for r in rows)
        raise PublishError(f"{len(rows)} releases are labelled {param!r} ({ids}); use --release-id")
    models = [
        r[0]
        for r in conn.execute(
            "SELECT m.slug FROM release_model rm JOIN model m ON m.id = rm.model_id "
            "WHERE rm.release_id = ? ORDER BY m.slug",
            (rows[0]["id"],),
        )
    ]
    stamp = _stamp(now)
    with conn:
        conn.execute("UPDATE release SET withdrawn_at = ? WHERE id = ?", (stamp, rows[0]["id"]))
    floor = conn.execute("SELECT max(id) FROM publication WHERE status = 'published'").fetchone()[0]
    _log(conn, "withdraw", f"v{floor or 0}", f"release #{rows[0]['id']} {rows[0]['label']}", now)
    return models
