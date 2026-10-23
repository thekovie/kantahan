import pytest
from pdfgen import make_overprint_pdf, make_pdf

from kantahan_catalog.extract import (
    MAX_PAGES,
    NUMBER_CELL,
    STRAY_TOKEN,
    _overprinted_rows,
    extract_rows,
    table_template,
)
from kantahan_catalog.models import ExtractionError


def rows_of(path):
    return [(r.number, r.title, r.artist) for r in extract_rows(path).rows]


def test_reads_number_title_and_artist_per_row(tmp_path):
    table = [
        ("15682", "20 Million", "Rivermaya"),
        ("15683", "A Love Like This", "Dan Fogelberg"),
        ("15688", "A Love Like War", "All Time Low"),
    ]
    pdf = make_pdf(tmp_path / "a.pdf", [[table]])
    assert rows_of(pdf) == table


def test_wrapped_artist_lines_join_in_reading_order(tmp_path):
    table = [
        ("15562", "Alalay Ng Hari", "Glock-9 Ft.\nAllan Mitchel"),
        ("15563", "Dahilan", "Callalily"),
        ("15564", "Hello", "Sam\nConception &\nTippy Dos"),
    ]
    pdf = make_pdf(tmp_path / "w.pdf", [[table]])
    assert rows_of(pdf)[0][2] == "Glock-9 Ft. Allan Mitchel"
    assert rows_of(pdf)[2][2] == "Sam Conception & Tippy Dos"


def test_three_tables_per_page_keep_columns_separate(tmp_path):
    t1 = [("10001", "One", "Aa"), ("10002", "Two", "Bb")]
    t2 = [("10003", "Three", "Cc"), ("10004", "Four", "Dd")]
    t3 = [("10005", "Five", "Ee")]
    pdf = make_pdf(tmp_path / "c.pdf", [[t1, t2, t3]])
    assert rows_of(pdf) == t1 + t2 + t3


def test_leading_zeros_are_kept_as_text(tmp_path):
    table = [
        ("00589", "Hurting Each Other", "Carpenters"),
        ("03150", "Hurting Each Other", "Carpenters"),
    ]
    pdf = make_pdf(tmp_path / "z.pdf", [[table]])
    assert [r[0] for r in rows_of(pdf)] == ["00589", "03150"]


def test_same_title_with_different_numbers_stays_separate(tmp_path):
    table = [("00589", "Same Title", "Same Artist"), ("03150", "Same Title", "Same Artist")]
    pdf = make_pdf(tmp_path / "d.pdf", [[table]])
    assert len(rows_of(pdf)) == 2


def test_partial_last_table_on_later_page_still_found(tmp_path):
    full = [(f"2{i:04d}", f"Song {i}", "Artist") for i in range(8)]
    last = [("29999", "Only Row", "Solo")]
    pdf = make_pdf(tmp_path / "p.pdf", [[full, full, full], [last]])
    assert extract_rows(pdf).rows[-1].number == "29999"
    assert len(extract_rows(pdf).rows) == 25


def test_header_lines_are_returned(tmp_path):
    pdf = make_pdf(tmp_path / "h.pdf", [[[("15562", "A", "B")]]], header="Vol. 62 For Reyna ! 1")
    assert "Vol. 62 For Reyna ! 1" in extract_rows(pdf).header_lines


def test_stray_number_outside_tables_is_counted_not_imported(tmp_path):
    pdf = make_pdf(tmp_path / "s.pdf", [[[("15562", "A", "B")]]], stray="12345")
    result = extract_rows(pdf)
    assert [r.number for r in result.rows] == ["15562"]
    assert result.stray_tokens == 1


def test_overprinted_artist_flags_the_row_and_both_neighbours_but_not_distant_rows(tmp_path):
    rows = [(f"1500{i}", f"Song {i}", f"Artist {i}") for i in range(6)]
    pdf = make_overprint_pdf(tmp_path / "o.pdf", rows, extra="Nathan", row_index=2)
    flags = {r.number: r.flags for r in extract_rows(pdf).rows}
    assert all("overprint" in flags[n] for n in ("15001", "15002", "15003"))
    assert not flags["15000"] and not flags["15005"]


def test_overlap_between_words_assigned_to_different_rows_is_still_found():
    word = {"x0": 0, "x1": 20, "top": 0, "bottom": 10}
    other = {"x0": 5, "x1": 25, "top": 4, "bottom": 14}
    assert _overprinted_rows({0: [word], 1: [other]}, 4) == {0, 1, 2}


def test_overprinted_title_gets_its_own_flag(tmp_path):
    rows = [(f"1500{i}", f"Song {i}", "Artist") for i in range(4)]
    pdf = make_overprint_pdf(tmp_path / "t.pdf", rows, extra="Clash", row_index=1, column="title")
    flagged = [r for r in extract_rows(pdf).rows if "title_overprint" in r.flags]
    assert {r.number for r in flagged} >= {"15001"}


def test_number_patterns_accept_ascii_digits_only_and_no_trailing_newline():
    assert NUMBER_CELL.fullmatch("12345") and STRAY_TOKEN.fullmatch("12345")
    assert not NUMBER_CELL.fullmatch("\uff11\uff12\uff13\uff14\uff15")
    assert not STRAY_TOKEN.fullmatch("12345\n")


def test_documents_over_the_page_limit_are_rejected(tmp_path):
    page = [[("15001", "A", "B")]]
    pdf = make_pdf(tmp_path / "long.pdf", [page] * (MAX_PAGES + 1))
    with pytest.raises(ExtractionError, match="pages"):
        extract_rows(pdf)


def test_missing_last_border_is_reconstructed_only_when_it_stays_on_the_page():
    class Page:
        width = 612.0

        def __init__(self, xs):
            self.rects = [{"x0": x, "x1": x, "top": 0, "bottom": 20} for x in xs]
            self.lines = []

    ok = [14, 117, 159, 204, 211, 314, 356, 401, 407, 511, 553]
    assert len(table_template([Page(ok)])) == 3
    narrow = Page(ok)
    narrow.width = 560.0
    with pytest.raises(ExtractionError, match="outside the page"):
        table_template([narrow])


def test_document_without_tables_is_an_extraction_error(tmp_path):
    pdf = make_pdf(tmp_path / "e.pdf", [[]])
    with pytest.raises(ExtractionError):
        extract_rows(pdf)


def test_non_pdf_file_is_an_extraction_error(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"this is not a pdf")
    with pytest.raises(ExtractionError):
        extract_rows(bad)
