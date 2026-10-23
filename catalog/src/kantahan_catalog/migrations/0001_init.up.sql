-- Kantahan catalog schema. Song numbers are TEXT everywhere (leading zeros matter).

CREATE TABLE model_family (
    id    INTEGER PRIMARY KEY,
    slug  TEXT NOT NULL UNIQUE,
    name  TEXT NOT NULL
);

CREATE TABLE model (
    id            INTEGER PRIMARY KEY,
    family_id     INTEGER NOT NULL REFERENCES model_family(id),
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    variant_group TEXT,            -- NULL = variant not evidenced
    notes         TEXT
);

CREATE TABLE source (
    id            INTEGER PRIMARY KEY,
    slug          TEXT NOT NULL UNIQUE,
    base_url      TEXT NOT NULL,
    priority      TEXT NOT NULL,
    official      INTEGER NOT NULL DEFAULT 1,
    rights_status TEXT NOT NULL DEFAULT 'unresolved',
    notes         TEXT
);

-- One row per distinct file content. The same file linked from several sources is one document.
CREATE TABLE document (
    id              INTEGER PRIMARY KEY,
    sha256          TEXT NOT NULL UNIQUE,
    bytes           INTEGER NOT NULL,
    pages           INTEGER,
    file_key        TEXT,
    header_text     TEXT,
    header_family   TEXT,
    header_evidence TEXT,
    status          TEXT NOT NULL CHECK (status IN ('ok', 'quarantined')),
    first_seen      TEXT NOT NULL
);

CREATE TABLE document_link (
    id          INTEGER PRIMARY KEY,
    source_id   INTEGER NOT NULL REFERENCES source(id),
    document_id INTEGER REFERENCES document(id),
    url         TEXT NOT NULL,
    label       TEXT,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    removed_at  TEXT,
    UNIQUE (source_id, url)
);

-- A release is a published volume. 'held' = no evidence ties it to a model, so it is never built.
CREATE TABLE release (
    id          INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL UNIQUE REFERENCES document(id) ON DELETE CASCADE,
    label       TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'incremental' CHECK (kind IN ('base', 'incremental', 'unknown')),
    status      TEXT NOT NULL CHECK (status IN ('mapped', 'held'))
);

CREATE TABLE release_model (
    release_id INTEGER NOT NULL REFERENCES release(id) ON DELETE CASCADE,
    model_id   INTEGER NOT NULL REFERENCES model(id),
    evidence   TEXT NOT NULL,
    PRIMARY KEY (release_id, model_id)
);

-- Canonical songs: linked only when normalized title and artist are both present and equal.
CREATE TABLE song (
    id         INTEGER PRIMARY KEY,
    title_norm TEXT NOT NULL,
    artist_norm TEXT NOT NULL,
    UNIQUE (title_norm, artist_norm)
);

CREATE TABLE song_entry (
    id          INTEGER PRIMARY KEY,
    release_id  INTEGER NOT NULL REFERENCES release(id) ON DELETE CASCADE,
    song_id     INTEGER REFERENCES song(id),
    number      TEXT NOT NULL,
    title_raw   TEXT NOT NULL,
    artist_raw  TEXT NOT NULL,
    title_norm  TEXT NOT NULL,
    artist_norm TEXT NOT NULL,
    page        INTEGER,
    flags       TEXT NOT NULL DEFAULT '',
    UNIQUE (release_id, number)
);
CREATE INDEX idx_song_entry_number ON song_entry(number);

CREATE TABLE catalog_version (
    id              INTEGER PRIMARY KEY,
    created_at      TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('building', 'validated', 'published', 'withdrawn')),
    parent_id       INTEGER REFERENCES catalog_version(id),
    manifest_sha256 TEXT,
    notes           TEXT
);

CREATE TABLE catalog_version_model (
    version_id    INTEGER NOT NULL REFERENCES catalog_version(id) ON DELETE CASCADE,
    model_id      INTEGER NOT NULL REFERENCES model(id),
    bundle_sha256 TEXT NOT NULL,
    song_count    INTEGER NOT NULL,
    PRIMARY KEY (version_id, model_id)
);

CREATE TABLE quarantine (
    id           INTEGER PRIMARY KEY,
    document_id  INTEGER NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    reason       TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    resolved_at  TEXT
);

CREATE TABLE import_run (
    id          INTEGER PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('scheduled', 'manual', 'audit', 'local')),
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    outcome     TEXT,
    stats_json  TEXT
);
