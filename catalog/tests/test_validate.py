from kantahan_catalog.models import DocumentExtract, RawRow
from kantahan_catalog.validate import has_errors, validate_document


def row(number="15562", title="Song", artist="Artist", flags=()):
    return RawRow(number, title, artist, 1, 0, 0, tuple(flags))


def doc(*rows, stray=0):
    return DocumentExtract(tuple(rows), 1, (), stray)


def codes(issues):
    return {i.code for i in issues}


def test_clean_document_has_no_issues():
    assert validate_document(doc(row("15562"), row("15563"))) == []


def test_empty_document_is_an_error():
    issues = validate_document(doc())
    assert codes(issues) == {"no_rows"} and has_errors(issues)


def test_wrong_number_format_is_an_error():
    assert "bad_number" in codes(validate_document(doc(row("1234"), row("15563"))))


def test_leading_zero_numbers_are_valid():
    assert validate_document(doc(row("00589"), row("00590"))) == []


def test_missing_title_is_an_error():
    issues = validate_document(doc(row("15562", title=""), row("15563")))
    assert "missing_title" in codes(issues) and has_errors(issues)


def test_identical_duplicate_is_a_warning_conflicting_duplicate_is_an_error():
    same = validate_document(doc(row("15562"), row("15562")))
    assert codes(same) == {"duplicate_identical"} and not has_errors(same)
    diff = validate_document(doc(row("15562", title="A"), row("15562", title="B")))
    assert "duplicate_conflict" in codes(diff) and has_errors(diff)


def test_same_title_with_different_numbers_is_fine():
    assert validate_document(doc(row("15562", title="Same"), row("15563", title="Same"))) == []


def test_few_missing_artists_warn_many_error():
    rows = [row(f"{15000 + i}") for i in range(98)]
    few = validate_document(doc(*rows, row("15200", artist=""), row("15201", artist="")))
    assert codes(few) == {"missing_artist"} and not has_errors(few)
    many = validate_document(doc(*rows[:90], *[row(f"{15200 + i}", artist="") for i in range(10)]))
    assert "artist_missing_rate" in codes(many) and has_errors(many)


def test_overprint_rows_warn_that_artist_is_withheld():
    issues = validate_document(doc(row("15562", flags=["overprint"]), row("15563")))
    assert codes(issues) == {"artist_uncertain"} and not has_errors(issues)


def test_row_count_drop_against_previous_parse_is_an_error():
    rows = [row(f"{15000 + i}") for i in range(90)]
    assert "row_drop" in codes(validate_document(doc(*rows), previous_rows=100))
    assert validate_document(doc(*rows), previous_rows=91) == []


def test_range_outliers_and_stray_tokens_are_warnings():
    rows = [row(f"{15000 + i}") for i in range(20)] + [row("49006")]
    issues = validate_document(doc(*rows, stray=1))
    assert codes(issues) == {"range_outlier", "stray_tokens"} and not has_errors(issues)


def test_many_stray_tokens_block_the_document_because_rows_may_be_missing():
    rows = [row(f"{15000 + i}") for i in range(40)]
    assert has_errors(validate_document(doc(*rows, stray=4)))


def test_one_stray_token_is_tolerated_but_the_rate_still_applies():
    rows = [row(f"{15000 + i}") for i in range(300)]
    assert not has_errors(validate_document(doc(*rows, stray=1)))
    assert has_errors(validate_document(doc(*rows[:50], stray=2)))


def test_fullwidth_digits_are_not_a_valid_number():
    assert "bad_number" in codes(validate_document(doc(row("\uff11\uff12\uff13\uff14\uff15"))))


def test_overprinted_titles_warn_that_rows_are_left_out():
    issues = validate_document(doc(row("15001", flags=["title_overprint"]), row("15002")))
    assert "title_uncertain" in codes(issues) and not has_errors(issues)


def test_blank_artists_are_accepted_only_when_a_person_confirmed_the_document():
    rows = tuple(RawRow(f"{15000 + i}", f"Song {i}", "", 1, 0, i) for i in range(40))
    doc = DocumentExtract(rows, 1, ("Vol. 1",), 0)
    assert any(i.code == "artist_missing_rate" for i in validate_document(doc))
    reviewed = validate_document(doc, blank_artists_ok=True)
    assert not any(i.severity == "error" for i in reviewed)


def test_odd_rows_are_set_aside_only_while_they_are_few():
    from kantahan_catalog.models import DocumentExtract, RawRow
    from kantahan_catalog.validate import set_aside_odd_rows

    def row(n, title="T", artist="A"):
        return RawRow(n, title, artist, 1, 0, 0)

    good = tuple(row(f"{15000 + i}", f"T{i}") for i in range(40))
    few = DocumentExtract(good + (row("782"), row("15000", "Other")), 1, (), 0)
    kept, issues = set_aside_odd_rows(few)
    assert len(kept.rows) == 39 and {i.code for i in issues} == {
        "row_excluded_bad_number",
        "row_excluded_duplicate",
    }
    many = DocumentExtract(good[:10] + tuple(row(f"{100 + i}") for i in range(10)), 1, (), 0)
    unchanged, none = set_aside_odd_rows(many)
    assert unchanged is many and none == []


def test_column_header_text_inside_titles_or_artists_blocks_the_document_when_systematic():
    def rows_with(prefix, count, where="title"):
        out = []
        for i in range(30):
            leak = i < count
            title = f"{prefix if leak and where == 'title' else ''}Song {i}"
            artist = f"{prefix if leak and where == 'artist' else ''}Artist {i}"
            out.append(RawRow(f"{15000 + i}", title, artist, 1, 0, i))
        return DocumentExtract(tuple(out), 1, (), 0)

    systematic = validate_document(rows_with("Song Title ", 5))
    assert any(i.code == "header_text_leaked" and i.severity == "error" for i in systematic)
    artist = validate_document(rows_with("Popularized By: ", 5, "artist"))
    assert any(i.code == "header_text_leaked" and i.severity == "error" for i in artist)
    one = validate_document(rows_with("Song Title ", 1))
    assert any(i.code == "header_text_leaked" and i.severity == "warn" for i in one)
    assert not [i for i in validate_document(rows_with("", 0)) if i.code == "header_text_leaked"]
