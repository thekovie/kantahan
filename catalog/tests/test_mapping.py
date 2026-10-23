from conftest import sample_rows

from kantahan_catalog.discover import DiscoveredLink
from kantahan_catalog.importer import import_pdf
from kantahan_catalog.mapping import SECTION_TO_MODEL, apply_section_mappings


def link(n, section, source="a"):
    return DiscoveredLink(
        source=source,
        section=section,
        label=f"Volume {n}",
        url=f"https://www.mediafire.com/file/k{n}/f.pdf/file",
    )


def add(conn, path, n, header_label="Volume"):
    return import_pdf(
        conn,
        path,
        source_slug="a",
        url=f"https://www.mediafire.com/file/k{n}/f.pdf/file",
        label=f"{header_label} {n}",
    )


def models_of(conn, label):
    return [
        r[0]
        for r in conn.execute(
            "SELECT m.slug FROM release_model rm JOIN model m ON m.id = rm.model_id "
            "JOIN release r ON r.id = rm.release_id WHERE r.label = ? ORDER BY m.slug",
            (label,),
        )
    ]


def test_every_publisher_section_has_a_seeded_model(conn):
    slugs = {r[0] for r in conn.execute("SELECT slug FROM model")}
    assert set(SECTION_TO_MODEL.values()) <= slugs and len(slugs) == 12


def test_a_volume_joins_every_section_that_lists_it(conn, pdf):
    add(conn, pdf("a.pdf", sample_rows(30000, 5), header="Vol. 5 T-X Series ! 1"), 5)
    result = apply_section_mappings(
        conn, [link(5, "T-X SERIES"), link(5, "FLUTE/PIANO V1.5/PIANO XL SD/PK10")]
    )
    assert models_of(conn, "Volume 5") == ["flute-piano-piano-xl-sd-pk10", "t-x"]
    assert result.added == 2
    status = conn.execute("SELECT status FROM release").fetchone()[0]
    assert status == "mapped"
    evidence = conn.execute("SELECT evidence FROM release_model LIMIT 1").fetchone()[0]
    assert "listed under" in evidence and "publisher" in evidence


def test_mapping_twice_changes_nothing(conn, pdf):
    add(conn, pdf("a.pdf", sample_rows(30000, 5), header="Vol. 5 ! 1"), 5)
    links = [link(5, "BRAVO")]
    assert apply_section_mappings(conn, links).added == 1
    again = apply_section_mappings(conn, links)
    assert again.added == 0 and again.already == 1


def test_reyna_section_alone_is_not_evidence_for_reyna(conn, pdf):
    add(conn, pdf("a.pdf", sample_rows(30000, 5), header="Vol. 5 T-X Series ! 1"), 5)
    result = apply_section_mappings(conn, [link(5, "REYNA SERIES")])
    assert models_of(conn, "Volume 5") == [] and result.strict_skipped == 1
    assert conn.execute("SELECT status FROM release").fetchone()[0] == "held"


def test_reyna_header_evidence_still_maps_reyna_and_other_sections_add_more(conn, pdf):
    add(conn, pdf("a.pdf", sample_rows(15000, 5), header="Vol. 1 For Reyna ! 1"), 1)
    apply_section_mappings(conn, [link(1, "REYNA SERIES"), link(1, "P-SERIES")])
    assert models_of(conn, "Volume 1") == ["p-series", "reyna"]


def test_unknown_sections_documents_not_imported_and_other_sources_are_reported(conn, pdf):
    add(conn, pdf("a.pdf", sample_rows(30000, 5), header="Vol. 5 ! 1"), 5)
    result = apply_section_mappings(
        conn,
        [
            link(5, "SOMETHING NEW"),
            link(9, "BRAVO"),  # never imported (for example quarantined)
            link(5, "BRAVO", source="b"),  # only the publisher's own page counts
        ],
    )
    assert result.unknown_sections == ("SOMETHING NEW",)
    assert result.not_imported == 1 and result.added == 0
    assert models_of(conn, "Volume 5") == []
