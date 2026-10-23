# Catalog updates

> **Status: planned, not implemented (milestone M3).**

Server: scheduled check every 14 days plus a monthly audit and manual runs; changed documents are validated, and only validated releases are published as versioned bundles with a manifest. Client: load the local catalog immediately, check the manifest in the background, verify integrity, switch atomically, and keep the old catalog if anything fails. See [catalog-ingestion.md](catalog-ingestion.md) for the audited constraints (no ETag from the document host, rate limiting on the source site).
