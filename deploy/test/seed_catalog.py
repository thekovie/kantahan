"""Writes a tiny synthetic published catalog into /data/publish (smoke test only; not real data)."""

import hashlib
import json
from pathlib import Path

root = Path("/data/publish")
(root / "v1").mkdir(parents=True, exist_ok=True)
rows = [("00001", "Smoke Test Song One", "Synthetic Band"), ("00002", "Smoke Test Song Two", "Synthetic Band")]
bundle = {
    "schema": 1,
    "model": "reyna",
    "count": len(rows),
    "releases": ["Volume 1"],
    "n": [r[0] for r in rows],
    "t": [r[1] for r in rows],
    "a": [r[2] for r in rows],
    "r": [0 for _ in rows],
    "u": [0 for _ in rows],
}
payload = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
(root / "v1" / "reyna.json").write_bytes(payload)
manifest = {
    "schema": 1,
    "version": "v1",
    "generatedAt": "2026-10-24T00:00:00+00:00",
    "synthetic": True,
    "suspended": False,
    "source": {"label": "Synthetic smoke-test data", "url": "https://example.org/"},
    "models": [
        {
            "slug": "reyna",
            "name": "Reyna",
            "family": "Reyna series",
            "hue": "magenta",
            "file": "v1/reyna.json",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "songs": len(rows),
            "coverage": "Volume 1",
        }
    ],
}
(root / "manifest.json").write_text(json.dumps(manifest, indent=2))
print("seeded", sorted(p.name for p in root.iterdir()))
