import sqlite3

import pytest

from kantahan_catalog import db


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    yield c
    c.close()


def tables(c):
    return {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_migrate_applies_all_versions_in_order(conn):
    assert db.migrate(conn) == [1, 2, 3]
    assert {"document", "release", "song_entry", "quarantine", "catalog_version"} <= tables(conn)
    assert db.applied_versions(conn) == [1, 2, 3]


def test_migrate_is_idempotent(conn):
    db.migrate(conn)
    assert db.migrate(conn) == []


def test_seed_has_reyna_model_without_variant(conn):
    db.migrate(conn)
    row = conn.execute("SELECT variant_group FROM model WHERE slug = 'reyna'").fetchone()
    assert row["variant_group"] is None
    assert conn.execute("SELECT count(*) c FROM model_family").fetchone()["c"] == 12


def test_rollback_undoes_newest_first_and_can_reapply(conn):
    db.migrate(conn)
    assert db.rollback(conn, steps=1) == [3]
    assert "superseded_by" not in {r["name"] for r in conn.execute("PRAGMA table_info(release)")}
    assert db.rollback(conn, steps=1) == [2]
    assert conn.execute("SELECT count(*) c FROM model").fetchone()["c"] == 0
    assert db.rollback(conn, steps=1) == [1]
    assert "document" not in tables(conn)
    assert db.migrate(conn) == [1, 2, 3]


def test_migrate_target_stops_early(conn):
    assert db.migrate(conn, target=1) == [1]
    assert db.applied_versions(conn) == [1]


def test_failed_migration_leaves_no_partial_state(conn, monkeypatch):
    bad = db.Migration(
        1, "bad", "CREATE TABLE ok_table (id INTEGER);\nCREATE TABLE ok_table (id INTEGER);\n", ""
    )
    monkeypatch.setattr(db, "load_migrations", lambda: [bad])
    with pytest.raises(sqlite3.OperationalError):
        db.migrate(conn)
    assert "ok_table" not in tables(conn)
    assert db.applied_versions(conn) == []


def test_numbers_keep_leading_zeros(conn):
    db.migrate(conn)
    conn.execute(
        "INSERT INTO document (sha256, bytes, status, first_seen) VALUES ('h', 1, 'ok', 'now')"
    )
    conn.execute("INSERT INTO release (document_id, label, status) VALUES (1, 'Volume 1', 'held')")
    conn.execute(
        "INSERT INTO song_entry (release_id, number, title_raw, artist_raw, title_norm, artist_norm) "
        "VALUES (1, '00589', 't', 'a', 't', 'a')"
    )
    assert conn.execute("SELECT number FROM song_entry").fetchone()["number"] == "00589"


def test_same_number_twice_in_one_release_is_rejected(conn):
    db.migrate(conn)
    conn.execute(
        "INSERT INTO document (sha256, bytes, status, first_seen) VALUES ('h', 1, 'ok', 'now')"
    )
    conn.execute("INSERT INTO release (document_id, label, status) VALUES (1, 'V', 'held')")
    insert = (
        "INSERT INTO song_entry (release_id, number, title_raw, artist_raw, title_norm, artist_norm) "
        "VALUES (1, '15562', 't', 'a', 't', 'a')"
    )
    conn.execute(insert)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(insert)
