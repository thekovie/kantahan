"""SQLite connection and numbered migrations (each version has an up and a down script)."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

_FILE = re.compile(r"^(\d{4})_(\w+)\.(up|down)\.sql$")


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    up: str
    down: str


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def load_migrations() -> list[Migration]:
    scripts: dict[int, dict[str, str]] = {}
    for entry in resources.files("kantahan_catalog").joinpath("migrations").iterdir():
        match = _FILE.match(entry.name)
        if match:
            version, name, direction = int(match[1]), match[2], match[3]
            scripts.setdefault(version, {"name": name})[direction] = entry.read_text("utf-8")
    result = []
    for version in sorted(scripts):
        s = scripts[version]
        if "up" not in s or "down" not in s:
            raise RuntimeError(f"migration {version:04d} needs both an up and a down script")
        result.append(Migration(version, s["name"], s["up"], s["down"]))
    return result


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
    )
    conn.commit()


def applied_versions(conn: sqlite3.Connection) -> list[int]:
    _ensure_table(conn)
    return [r["version"] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY 1")]


def _run(conn: sqlite3.Connection, sql: str, bookkeeping: str, params: tuple[object, ...]) -> None:
    """Apply a script and its bookkeeping row atomically."""
    conn.commit()
    try:
        conn.execute("BEGIN")
        for statement in _statements(sql):
            conn.execute(statement)
        conn.execute(bookkeeping, params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _statements(sql: str) -> list[str]:
    """Split a script into statements using SQLite's own parser (safe for ';' inside strings)."""
    statements: list[str] = []
    buffer = ""
    for line in sql.splitlines(keepends=True):
        if not buffer and (not line.strip() or line.lstrip().startswith("--")):
            continue
        buffer += line
        if sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        raise ValueError("migration script ends with an incomplete statement")
    return statements


def migrate(conn: sqlite3.Connection, target: int | None = None) -> list[int]:
    """Apply pending migrations up to `target` (default: all). Returns versions applied."""
    done = set(applied_versions(conn))
    applied: list[int] = []
    for m in load_migrations():
        if m.version in done or (target is not None and m.version > target):
            continue
        now = datetime.now(UTC).isoformat(timespec="seconds")
        _run(
            conn,
            m.up,
            "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
            (m.version, m.name, now),
        )
        applied.append(m.version)
    return applied


def rollback(conn: sqlite3.Connection, steps: int = 1) -> list[int]:
    """Undo the most recent `steps` migrations. Returns versions reverted, newest first."""
    by_version = {m.version: m for m in load_migrations()}
    reverted: list[int] = []
    for version in reversed(applied_versions(conn)[-steps:] if steps > 0 else []):
        _run(
            conn,
            by_version[version].down,
            "DELETE FROM schema_migrations WHERE version = ?",
            (version,),
        )
        reverted.append(version)
    return reverted
