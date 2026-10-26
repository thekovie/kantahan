# Database schema

SQLite, created by numbered migrations in [`catalog/src/kantahan_catalog/migrations/`](../catalog/src/kantahan_catalog/migrations/). Every version has an `.up.sql` and a `.down.sql`; `kantahan-catalog migrate` applies pending versions and `migrate --down N` reverts the newest N. A failed migration leaves no partial state (script and bookkeeping row commit together). Implemented in milestone M1.

| Version | Content |
|---|---|
| 0001 | all tables below |
| 0002 | seed: the 12 model families named by the official archive, and one model, `reyna` |
| 0003 | `release.superseded_by`: a newer document for the same file retires the older release |

## Concepts

| Table | Purpose |
|---|---|
| `model_family`, `model` | families named by Source A; models users can select. Only `reyna` exists, with no variant (`variant_group` NULL), because the audit evidences the family but not Reyna 2/3C/SE vs Reyna 3/4 |
| `source` | registry of approved source pages (A, B, C ...) with rights status, default `unresolved` |
| `document` | one row per distinct file content (`sha256` unique): size, pages, file key, page-1 header text, header family and the line that justified it, status `ok` or `quarantined` |
| `document_link` | where a document was found: one row per `(source, url)`, with first/last seen. The same file listed by sources A, B and C is one document with three links |
| `release` | a published volume (`label` such as "Volume 62", `kind` base/incremental/unknown) backed by one document. `status` is `mapped` (header evidence ties it to a model) or `held` (no evidence, never built); `superseded_by` is set when a newer document replaces it, and superseded releases are never built |
| `release_model` | the evidence row tying a release to a model, with the header line as text |
| `song_entry` | a row as printed: `number` (TEXT, leading zeros kept), raw title and artist, folded title/artist for matching, page, `flags`. Unique per `(release, number)` |
| `song` | canonical song, created only when folded title and artist are both non-empty and equal. Entries are linked, never merged or dropped: the same title under different numbers stays separate |
| `model` (13 rows after migration 0006), `release_model` | one model per publisher machine group; `release_model.evidence` says why a release belongs to it ("page-1 header: ..." for Reyna, "listed under ..." for the others); see [model-compatibility.md](model-compatibility.md) |
| `publication`, `publication_event` | M3: one row per published catalog (`v<id>`, status, manifest hash) and a log of rollback, suspend, resume and withdraw actions (migration 0004) |
| `catalog_version`, `catalog_version_model` | local build records: status `building`/`validated`/`published`/`withdrawn`, parent version, bundle SHA-256 and song count per model |
| `quarantine` | documents rejected by validation, with reason and sample details |
| `import_run` | reserved for the scheduled runs in M3; not written yet |

## Invariants

- Song numbers are text. `00589` and `589` are different numbers.
- A model's songs come only from `mapped` releases.
- Nothing is ever deduplicated across models; `song_entry` rows belong to a release.
- A quarantined document has no release and no entries.
- `flags` may contain `overprint` (artist text overlap that could not be resolved: artist kept in the database, withheld from bundles) and `title_overprint` (unresolved title overlap: row left out of bundles). Rare after the overlap rule: 12 of 12,489 rows in the audited documents.

## Bundle format (local build output, schema 1)

`kantahan-catalog build` writes an immutable `work/releases/<model>.v<N>.json` per build and, for a validated build only, atomically replaces `work/releases/<model>.json` (never committed): columnar arrays `n` numbers, `t` titles, `a` artists (empty when withheld), `r` index into `releases`, `u` 1 when the artist is withheld, plus `count`, `model`, `schema`. Keys are sorted, so the same input gives the same bytes and SHA-256. `kantahan-catalog publish` builds every model listed in `display.yaml` into `work/publish/v<N>/` and writes the manifest the app reads; see [catalog-updates.md](catalog-updates.md). Bundles are served as plain JSON (the web server compresses them); the manifest carries the SHA-256 of the exact bytes. `release.withdrawn_at` (migration 0004) leaves a release out of every later build.
