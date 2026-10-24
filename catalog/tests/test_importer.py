import hashlib
import json

from conftest import sample_rows

from kantahan_catalog.importer import import_pdf

URL = "https://www.mediafire.com/file/abc123/Reyna_Volume_1.pdf/file"


def run(conn, path, url=URL, source="a", label="Volume 1"):
    return import_pdf(conn, path, source_slug=source, url=url, label=label)


def count(conn, table):
    return conn.execute(f"SELECT count(*) c FROM {table}").fetchone()["c"]


def test_reyna_header_imports_a_mapped_release_with_evidence(conn, pdf):
    rows = [("00589", "Hurting Each Other", "Carpenters"), ("00590", "Dati", "Sam Conception")]
    result = run(conn, pdf("r.pdf", rows))
    assert (result.outcome, result.status, result.rows) == ("imported", "mapped", 2)
    ev = conn.execute("SELECT evidence FROM release_model").fetchone()["evidence"]
    assert "For Reyna" in ev
    assert [r["number"] for r in conn.execute("SELECT number FROM song_entry ORDER BY id")] == [
        "00589",
        "00590",
    ]
    doc = conn.execute("SELECT file_key, header_family FROM document").fetchone()
    assert (doc["file_key"], doc["header_family"]) == ("abc123", "reyna")


def test_other_family_header_is_held_with_no_model_evidence(conn, pdf):
    result = run(conn, pdf("t.pdf", sample_rows(), header="! Vol 98 T-X Series"))
    assert (result.outcome, result.status) == ("imported", "held")
    assert count(conn, "release_model") == 0
    assert count(conn, "song_entry") == 6


def test_unstated_header_is_held(conn, pdf):
    assert run(conn, pdf("u.pdf", sample_rows(), header="! Volume 85")).status == "held"


def test_same_bytes_are_not_imported_twice(conn, pdf):
    path = pdf("r.pdf", sample_rows())
    run(conn, path)
    again = run(conn, path)
    assert again.outcome == "unchanged" and again.rows == 6
    assert (count(conn, "document"), count(conn, "release"), count(conn, "song_entry")) == (1, 1, 6)


def test_same_file_from_two_sources_is_one_document_with_two_links(conn, pdf):
    path = pdf("r.pdf", sample_rows())
    run(conn, path, source="a")
    run(conn, path, source="b", url="https://example.test/other.pdf")
    assert count(conn, "document") == 1 and count(conn, "document_link") == 2


def test_conflicting_duplicate_numbers_quarantine_the_document(conn, pdf):
    rows = [("15001", "One", "A"), ("15001", "Different", "B")]
    result = run(conn, pdf("d.pdf", rows))
    assert result.outcome == "quarantined"
    assert (count(conn, "release"), count(conn, "song_entry")) == (0, 0)
    reasons = {r["reason"] for r in conn.execute("SELECT reason FROM quarantine")}
    assert "duplicate_conflict" in reasons
    assert conn.execute("SELECT status FROM document").fetchone()["status"] == "quarantined"


def test_unreadable_document_is_quarantined_not_raised(conn, tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    result = run(conn, bad)
    assert result.outcome == "quarantined"
    details = json.loads(
        conn.execute("SELECT details_json FROM quarantine").fetchone()["details_json"]
    )
    assert details["count"] == 1


def test_same_song_text_links_to_one_canonical_song_but_keeps_both_numbers(conn, pdf):
    rows = [
        ("00589", "Hurting Each Other", "Carpenters"),
        ("03150", "Hurting each other", "CARPENTERS"),
    ]
    run(conn, pdf("s.pdf", rows))
    assert count(conn, "song") == 1
    assert count(conn, "song_entry") == 2
    assert conn.execute("SELECT count(DISTINCT song_id) c FROM song_entry").fetchone()["c"] == 1


def test_different_artists_never_share_a_canonical_song(conn, pdf):
    rows = [("15001", "Hello", "Adele"), ("15002", "Hello", "Lionel Richie")]
    run(conn, pdf("h.pdf", rows))
    assert count(conn, "song") == 2


def test_row_count_drop_on_a_changed_document_is_quarantined(conn, pdf):
    run(conn, pdf("v1.pdf", sample_rows(count=40)))
    shrunk = run(conn, pdf("v2.pdf", sample_rows(count=30)))
    assert shrunk.outcome == "quarantined"
    assert "row_drop" in {r["reason"] for r in conn.execute("SELECT reason FROM quarantine")}
    assert count(conn, "song_entry") == 40


def test_unknown_source_is_a_clear_error(conn, pdf):
    import pytest

    with pytest.raises(KeyError, match="unknown source"):
        run(conn, pdf("r.pdf", sample_rows()), source="nope")


def test_identical_duplicate_number_imports_once_instead_of_crashing(conn, pdf):
    rows = [("15001", "Same", "Artist"), ("15001", "Same", "Artist"), ("15002", "Other", "Artist")]
    result = run(conn, pdf("dup.pdf", rows))
    assert result.outcome == "imported" and count(conn, "song_entry") == 2


def test_row_drop_baseline_survives_a_quarantined_redownload(conn, pdf):
    run(conn, pdf("v1.pdf", sample_rows(count=40)))
    first = run(conn, pdf("v2.pdf", sample_rows(count=30, prefix="Other")))
    second = run(conn, pdf("v3.pdf", sample_rows(count=30, prefix="Different")))
    assert (first.outcome, second.outcome) == ("quarantined", "quarantined")
    assert count(conn, "release") == 1


def test_a_newer_document_supersedes_the_older_release(conn, pdf):
    rows = sample_rows(count=5)
    run(conn, pdf("v1.pdf", rows))
    fixed = [(n, "Corrected" if n == "15001" else t, a) for n, t, a in rows]
    result = run(conn, pdf("v2.pdf", fixed))
    assert result.outcome == "imported"
    live = conn.execute("SELECT id FROM release WHERE superseded_by IS NULL").fetchall()
    assert [r["id"] for r in live] == [result.release_id]
    assert count(conn, "release") == 2


def test_quarantined_document_is_reevaluated_only_when_asked(conn, pdf, monkeypatch):
    from kantahan_catalog import importer
    from kantahan_catalog.models import ExtractionError

    path = pdf("r.pdf", sample_rows())
    with monkeypatch.context() as m:
        m.setattr(
            importer, "extract_rows", lambda p: (_ for _ in ()).throw(ExtractionError("boom"))
        )
        assert run(conn, path).outcome == "quarantined"
    assert run(conn, path).outcome == "unchanged"  # same bytes, left alone by default
    again = import_pdf(
        conn, path, source_slug="a", url=URL, label="Volume 1", retry_quarantined=True
    )
    assert again.outcome == "imported" and count(conn, "document") == 1
    assert count(conn, "quarantine") == 0


def test_overprinted_title_rows_get_no_canonical_song(conn, pdf):
    rows = sample_rows(count=3)
    run(conn, pdf("r.pdf", rows))
    assert count(conn, "song") == 3


def test_reimport_replaces_rows_that_an_older_extractor_got_wrong(conn, pdf):
    path = pdf("a.pdf", [("15001", "Dati", "Sam Conception"), ("15002", "Dahilan", "Hunyo")])
    import_pdf(conn, path, source_slug="a", url=URL, label="Volume 1")
    conn.execute("UPDATE song_entry SET artist_raw = 'Conc' WHERE number = '15001'")
    unchanged = import_pdf(conn, path, source_slug="a", url=URL, label="Volume 1")
    assert unchanged.outcome == "unchanged"
    assert (
        conn.execute("SELECT artist_raw FROM song_entry WHERE number='15001'").fetchone()[0]
        == "Conc"
    )

    again = import_pdf(conn, path, source_slug="a", url=URL, label="Volume 1", reimport=True)
    assert again.outcome == "imported" and again.rows == 2
    artist = conn.execute("SELECT artist_raw FROM song_entry WHERE number='15001'").fetchone()[0]
    assert artist == "Sam Conception"
    assert conn.execute("SELECT count(*) FROM release").fetchone()[0] == 1


def test_reimport_keeps_a_withdrawal_and_every_sections_link(conn, pdf):
    path = pdf("a.pdf", [("15001", "Dati", "Sam Conception"), ("15002", "Dahilan", "Hunyo")])
    import_pdf(conn, path, source_slug="a", url=URL, label="Volume 1")
    other = "https://www.mediafire.com/file/zzz999/Other_Section_Link.pdf/file"
    import_pdf(conn, path, source_slug="a", url=other, label="Volume 1 again")
    conn.execute("UPDATE release SET withdrawn_at = '2026-10-01'")
    conn.commit()

    again = import_pdf(conn, path, source_slug="a", url=URL, label="Volume 1", reimport=True)
    assert again.outcome == "imported"
    assert conn.execute("SELECT withdrawn_at FROM release").fetchone()[0] == "2026-10-01"
    linked = conn.execute("SELECT count(*) FROM document_link WHERE document_id IS NOT NULL")
    assert linked.fetchone()[0] == 2  # both URLs still point at the one document


def test_reimport_never_replaces_a_working_import_with_a_rejected_one(conn, pdf, monkeypatch):
    from kantahan_catalog import importer as importer_module
    from kantahan_catalog.extract import extract_rows as real
    from kantahan_catalog.models import DocumentExtract

    rows = [(str(15000 + i), f"Song {i}", "Artist") for i in range(50)]
    path = pdf("a.pdf", rows)
    import_pdf(conn, path, source_slug="a", url=URL, label="Volume 1")

    def worse(source):
        read = real(source)  # an extractor that now loses most of the rows
        return DocumentExtract(read.rows[:20], read.pages, read.header_lines, read.stray_tokens)

    monkeypatch.setattr(importer_module, "extract_rows", worse)
    result = import_pdf(conn, path, source_slug="a", url=URL, label="Volume 1", reimport=True)
    assert result.outcome == "rejected"
    assert conn.execute("SELECT count(*) FROM song_entry").fetchone()[0] == 50
    assert conn.execute("SELECT status FROM document").fetchone()[0] == "ok"


def test_blank_artists_are_accepted_only_for_the_reviewed_file_content(conn, pdf):
    rows = [(str(15000 + i), f"Song {i}", "") for i in range(30)]
    path = pdf("blank.pdf", rows)
    rejected = import_pdf(conn, path, source_slug="a", url=URL, label="Volume 1")
    assert rejected.outcome == "quarantined"
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    accepted = import_pdf(
        conn,
        path,
        source_slug="a",
        url=URL,
        label="Volume 1",
        retry_quarantined=True,
        blank_artist_hashes={sha},
    )
    assert accepted.outcome == "imported"
    other = pdf("other.pdf", [(str(16000 + i), f"Song {i}", "") for i in range(30)])
    again = import_pdf(
        conn,
        other,
        source_slug="a",
        url="https://www.mediafire.com/file/other/f.pdf/file",
        label="Volume 2",
        blank_artist_hashes={sha},
    )
    assert again.outcome == "quarantined"
