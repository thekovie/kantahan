-- A release is superseded when a newer document replaces the file behind the same link.
-- Superseded releases are kept as history but never built. No FOREIGN KEY on purpose:
-- SQLite cannot drop a column that carries one, and the down script must work.
ALTER TABLE release ADD COLUMN superseded_by INTEGER;
