import pytest
from pdfgen import make_pdf

from kantahan_catalog.extract import (
    MAX_PAGES,
    NUMBER_CELL,
    STRAY_TOKEN,
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


def rows_by_number(path):
    return {r.number: r for r in extract_rows(path).rows}


def test_stack_overflowing_into_the_next_row_is_given_back_to_its_own_row(tmp_path):
    rows = [
        ("15000", "Song 0", "A1\nA2\nA3\nA4\nA5"),  # five lines overflow into the next row
        ("15001", "Song 1", "B1"),
        ("15002", "Song 2", "C1"),
    ]
    got = rows_by_number(make_pdf(tmp_path / "o.pdf", [[rows]]))
    assert got["15000"].artist == "A1 A2 A3 A4 A5"
    assert got["15001"].artist == "B1"
    assert not any(r.flags for r in got.values())


def test_words_on_the_same_text_line_stay_together_even_if_only_one_overlaps(tmp_path):
    rows = [
        ("15000", "Song 0", "A1\nA2\nA3\nA4\nAa Bb"),
        ("15001", "Song 1", "Aa"),
        ("15002", "Song 2", "C1"),
    ]
    got = rows_by_number(make_pdf(tmp_path / "s.pdf", [[rows]]))
    assert got["15000"].artist.endswith("Aa Bb")
    assert got["15001"].artist == "Aa"


def test_wrapped_title_overflowing_into_the_next_row_is_recovered(tmp_path):
    rows = [
        ("15000", "T1\nT2\nT3\nT4", "A"),
        ("15001", "U1", "B"),
        ("15002", "V1", "C"),
    ]
    got = rows_by_number(make_pdf(tmp_path / "t.pdf", [[rows]]))
    assert got["15000"].title == "T1 T2 T3 T4"
    assert got["15001"].title == "U1"
    assert not any(r.flags for r in got.values())


def test_overlap_that_cannot_be_placed_between_two_rows_stays_flagged():
    from kantahan_catalog.extract import _assign_cell

    first = {"x0": 0, "x1": 20, "top": 0.0, "bottom": 10.0, "_i": 0}
    second = {"x0": 5, "x1": 25, "top": 2.0, "bottom": 12.0, "_i": 1}
    rows, unresolved = _assign_cell([first, second], cy=[5.0], pitch=20.0)
    assert unresolved == {0} and rows[0]


def test_word_split_across_lines_is_joined_but_a_standalone_x_is_kept(tmp_path):
    rows = [
        ("15000", "Song 0", "The Chainsmoker\ns"),
        ("15001", "Song 1", "Nik Makino\nx Trey"),
        ("15002", "Song 2", "C1"),
    ]
    got = rows_by_number(make_pdf(tmp_path / "w.pdf", [[rows]]))
    assert got["15000"].artist == "The Chainsmokers"
    assert got["15001"].artist == "Nik Makino x Trey"
