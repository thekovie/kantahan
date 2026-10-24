"""Tie imported volumes to machine models through the publisher's own song list page.

The publisher (Source A) groups its documents by machine group. A volume that is listed under a
group joins that group's model, with the listing recorded as the evidence. This is the publisher's
statement, not something verified here, and a file may be listed under several groups.

Reyna is the exception, by the owner's decision (2026-10-24): its section alone is not enough,
because Source D sells separate Reyna and T-X volumes. A volume joins `reyna` only when its own
page-1 header says so, which the importer already records.

Mappings are only ever added: a link that disappears from the page does not remove songs.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass

from .discover import DiscoveredLink

SECTION_TO_MODEL: dict[str, str] = {
    "MAJOR/ALPHA/CELLO/X3/PIANO XL HDD": "major-alpha-cello-x3-piano-xl-hdd",
    "FLUTE/PIANO V1.5/PIANO XL SD/PK10": "flute-piano-piano-xl-sd-pk10",
    "KS-100 MINIBOX / KS-10 MINI SD": "ks-100-ks-10-mini-sd",
    "REYNA SERIES": "reyna",
    "T-X SERIES": "t-x",
    "KS-40 / KBOX-2 / KBOX-3": "ks-40-kbox",
    "KS-5 / JUNIOR LITE / KS-10 / JUNIOR 2": "ks-5-junior",
    "BMB / X2 / X1 / HDD": "bmb-x2-x1-hdd",
    "HERMOSA / N20 NANO PLUS": "hermosa-n20-nano-plus",
    "HOME 40 / NANO OLD": "home-40-nano-old",
    "BRAVO": "bravo",
    "P-SERIES": "p-series",
}

# Models that need their own header to say so; being listed in the section is not enough.
HEADER_ONLY_MODELS = frozenset({"reyna"})


@dataclass(frozen=True)
class MapResult:
    added: int
    already: int
    strict_skipped: int
    not_imported: int
    unknown_sections: tuple[str, ...]


def apply_section_mappings(conn: sqlite3.Connection, links: Iterable[DiscoveredLink]) -> MapResult:
    added = already = strict = missing = 0
    unknown: list[str] = []
    models = {r[0] for r in conn.execute("SELECT slug FROM model")}
    for link in links:
        if link.source != "a":  # B and C only repeat what A lists
            continue
        slug = SECTION_TO_MODEL.get(link.section)
        if slug is not None and slug not in models:
            raise KeyError(f"section {link.section!r} maps to {slug!r}, which has no model row")
        if slug is None:
            if link.section not in unknown:
                unknown.append(link.section)
            continue
        if slug in HEADER_ONLY_MODELS:
            strict += 1
            continue
        release = conn.execute(
            "SELECT r.id FROM document_link dl JOIN source s ON s.id = dl.source_id "
            "JOIN release r ON r.document_id = dl.document_id "
            "WHERE s.slug = 'a' AND dl.url = ? AND r.superseded_by IS NULL",
            (link.url,),
        ).fetchone()
        if release is None:
            missing += 1
            continue
        with conn:
            inserted = conn.execute(
                "INSERT OR IGNORE INTO release_model (release_id, model_id, evidence) "
                "SELECT ?, id, ? FROM model WHERE slug = ?",
                (
                    release["id"],
                    f"listed under '{link.section}' on the publisher's song list page (source A)",
                    slug,
                ),
            ).rowcount
            conn.execute(
                "UPDATE release SET status = 'mapped' WHERE id = ? AND status = 'held'",
                (release["id"],),
            )
        added, already = added + inserted, already + (1 - inserted)
    return MapResult(added, already, strict, missing, tuple(unknown))
