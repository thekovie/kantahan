# Database schema

> **Status: planned, not implemented.** The SQLite schema is built in milestone M1 and this page will then be generated from the real migrations.

Planned concepts (separate tables): model families; models and variants; catalog sources; source documents (URL, SHA-256, size); song releases and volumes; model-specific song entries; canonical songs (only conservative matches, never merged across distinct recordings); published catalog versions; quarantine records; import runs. Song numbers are stored as text to keep leading zeros. Migrations are numbered with down scripts.
