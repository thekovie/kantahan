# Troubleshooting

> **Status: stub.** Entries are added as real failure modes are met.

- **HTTP 429 from platinumkaraoke.com during an audit:** the site rate-limits automated requests (`Retry-After: 60`). Wait, reduce the request rate and retry; do not parallelise.
- **Empty reply from MediaFire:** seen once; retry after a short delay.
- **`pip` or `uv` hangs while installing packages in the audit environment:** observed once; not diagnosed.
