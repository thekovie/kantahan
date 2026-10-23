-- Publishing: each published catalog is a numbered publication ("v<id>"). Administrative actions
-- (rollback, suspend, resume, withdraw) are logged. A withdrawn release is never built.
ALTER TABLE release ADD COLUMN withdrawn_at TEXT;

CREATE TABLE publication (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('building', 'published', 'failed')),
    manifest_sha256 TEXT,
    notes           TEXT
);

CREATE TABLE publication_event (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    at      TEXT NOT NULL,
    action  TEXT NOT NULL CHECK (action IN ('rollback', 'suspend', 'resume', 'withdraw')),
    version TEXT,
    detail  TEXT
);
