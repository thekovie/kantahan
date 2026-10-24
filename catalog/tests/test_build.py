import hashlib
import json

import pytest
from conftest import sample_rows

from kantahan_catalog.build import BuildError, build_bundle
from kantahan_catalog.importer import import_pdf


def add(conn, path, n, header_label="Volume"):
    return import_pdf(
        conn,
        path,
        source_slug="a",
        url=f"https://www.mediafire.com/file/k{n}/f.pdf/file",
        label=f"{header_label} {n}",
    )


def load(result):
    return json.loads(result.path.read_text("utf-8"))


def test_bundle_has_numbers_as_strings_in_order(conn, pdf, tmp_path):
    rows = [("00589", "Hurting Each Other", "Carpenters"), ("15001", "Dati", "Sam Conception")]
    add(conn, pdf("a.pdf", rows), 1)
    result = build_bundle(conn, "reyna", tmp_path / "out")
    bundle = load(result)
    assert bundle["n"] == ["00589", "15001"] and bundle["count"] == 2
    assert bundle["t"][0] == "Hurting Each Other" and bundle["a"][1] == "Sam Conception"
    assert result.status == "validated"
    assert hashlib.sha256(result.path.read_bytes()).hexdigest() == result.sha256


def test_held_releases_never_enter_the_bundle(conn, pdf, tmp_path):
    add(conn, pdf("a.pdf", sample_rows(15000, 3)), 1)
    add(conn, pdf("b.pdf", sample_rows(16000, 3), header="! Vol 98 T-X Series"), 2)
    bundle = load(build_bundle(conn, "reyna", tmp_path))
    assert all(n.startswith("150") for n in bundle["n"])


def test_overprinted_artist_is_withheld_but_number_and_title_stay(conn, pdf, tmp_path, monkeypatch):
    add(conn, pdf("a.pdf", sample_rows(15000, 3)), 1)
    conn.execute("UPDATE song_entry SET flags = 'overprint' WHERE number = '15001'")
    result = build_bundle(conn, "reyna", tmp_path)
    bundle = load(result)
    i = bundle["n"].index("15001")
    assert bundle["a"][i] == "" and bundle["u"][i] == 1 and bundle["t"][i] == "Song 1"
    assert result.artists_withheld == 1


def test_identical_relisting_collapses_to_one_entry(conn, pdf, tmp_path):
    add(conn, pdf("a.pdf", [("15001", "Same", "Artist"), ("15002", "Other", "Artist")]), 1)
    add(conn, pdf("b.pdf", [("15001", "Same", "Artist"), ("15003", "New", "Artist")]), 2)
    result = build_bundle(conn, "reyna", tmp_path)
    assert load(result)["n"] == ["15001", "15002", "15003"] and result.status == "validated"


def test_conflicting_relisting_is_excluded_and_not_validated(conn, pdf, tmp_path):
    add(conn, pdf("a.pdf", [("15001", "Original", "Artist"), ("15002", "Fine", "Artist")]), 1)
    add(conn, pdf("b.pdf", [("15001", "Changed", "Artist"), ("15003", "New", "Artist")]), 2)
    result = build_bundle(conn, "reyna", tmp_path)
    assert result.conflicts == ("15001",) and result.status == "building"
    assert "15001" not in load(result)["n"]


def test_no_mapped_songs_is_an_error(conn, tmp_path):
    with pytest.raises(BuildError, match="no mapped releases"):
        build_bundle(conn, "reyna", tmp_path)


def test_unknown_model_is_an_error(conn, tmp_path):
    with pytest.raises(BuildError, match="unknown model"):
        build_bundle(conn, "nope", tmp_path)


def test_each_build_records_a_version_linked_to_the_previous(conn, pdf, tmp_path):
    add(conn, pdf("a.pdf", sample_rows()), 1)
    first = build_bundle(conn, "reyna", tmp_path)
    second = build_bundle(conn, "reyna", tmp_path)
    parent = conn.execute(
        "SELECT parent_id FROM catalog_version WHERE id = ?", (second.version_id,)
    ).fetchone()
    assert parent["parent_id"] == first.version_id
    assert (
        conn.execute(
            "SELECT song_count FROM catalog_version_model WHERE version_id = ?", (first.version_id,)
        ).fetchone()[0]
        == 6
    )


def test_superseded_release_is_not_built_and_fixes_replace_old_text(conn, pdf, tmp_path):
    rows = sample_rows(15000, 4)
    import_pdf(
        conn,
        pdf("v1.pdf", rows),
        source_slug="a",
        url="https://www.mediafire.com/file/same/f.pdf/file",
        label="Volume 1",
    )
    fixed = [(n, "Corrected" if n == "15001" else t, a) for n, t, a in rows]
    import_pdf(
        conn,
        pdf("v2.pdf", fixed),
        source_slug="a",
        url="https://www.mediafire.com/file/same/f.pdf/file",
        label="Volume 1",
    )
    result = build_bundle(conn, "reyna", tmp_path)
    bundle = load(result)
    assert result.status == "validated" and result.conflicts == ()
    assert bundle["t"][bundle["n"].index("15001")] == "Corrected"


def test_rows_with_uncertain_titles_are_left_out(conn, pdf, tmp_path):
    add(conn, pdf("a.pdf", sample_rows(15000, 3)), 1)
    conn.execute("UPDATE song_entry SET flags = 'title_overprint' WHERE number = '15001'")
    result = build_bundle(conn, "reyna", tmp_path)
    assert "15001" not in load(result)["n"] and result.titles_excluded == 1


def test_conflicted_build_never_overwrites_the_stable_bundle(conn, pdf, tmp_path):
    add(conn, pdf("a.pdf", [("15001", "Original", "A"), ("15002", "Fine", "A")]), 1)
    good = build_bundle(conn, "reyna", tmp_path)
    stable = (tmp_path / "reyna.json").read_bytes()
    add(conn, pdf("b.pdf", [("15001", "Changed", "A"), ("15003", "New", "A")]), 2)
    bad = build_bundle(conn, "reyna", tmp_path)
    assert (bad.status, bad.path.name) == ("building", f"reyna.v{bad.version_id}.json")
    assert (tmp_path / "reyna.json").read_bytes() == stable
    assert good.path.name == "reyna.json"


def test_recorded_hash_matches_an_immutable_versioned_file(conn, pdf, tmp_path):
    add(conn, pdf("a.pdf", sample_rows()), 1)
    first = build_bundle(conn, "reyna", tmp_path)
    add(conn, pdf("b.pdf", sample_rows(16000, 3)), 2)
    build_bundle(conn, "reyna", tmp_path)
    old = tmp_path / f"reyna.v{first.version_id}.json"
    assert hashlib.sha256(old.read_bytes()).hexdigest() == first.sha256


def test_same_title_with_different_artist_text_keeps_the_song_and_withholds_the_artist(
    conn, pdf, tmp_path
):
    add(conn, pdf("a.pdf", [("15001", "Indigo", "keshi"), ("15002", "Fine", "Artist")]), 1)
    add(conn, pdf("b.pdf", [("15001", "Indigo", "keshi Rascal Flatts,")]), 2)
    result = build_bundle(conn, "reyna", tmp_path)
    bundle = load(result)
    i = bundle["n"].index("15001")
    assert bundle["t"][i] == "Indigo" and bundle["a"][i] == "" and bundle["u"][i] == 1
    assert result.conflicts == () and result.status == "validated"
    assert result.artists_withheld == 1


def test_a_few_title_conflicts_can_be_tolerated_when_the_caller_allows_a_share(conn, pdf, tmp_path):
    rows = [(str(15000 + i), f"Song {i}", "Artist") for i in range(50)]
    add(conn, pdf("a.pdf", rows), 1)
    add(conn, pdf("b.pdf", [("15001", "A different song", "Other")]), 2)
    strict = build_bundle(conn, "reyna", tmp_path / "strict")
    assert strict.status == "building" and strict.conflicts == ("15001",)
    lenient = build_bundle(conn, "reyna", tmp_path / "lenient", max_conflict_share=0.05)
    assert lenient.status == "validated" and lenient.conflicts == ("15001",)
    assert "15001" not in load(lenient)["n"] and len(load(lenient)["n"]) == 49


def test_too_many_title_conflicts_are_never_tolerated(conn, pdf, tmp_path):
    rows = [(str(15000 + i), f"Song {i}", "Artist") for i in range(50)]
    add(conn, pdf("a.pdf", rows), 1)
    clash = [(str(15000 + i), f"Other {i}", "Other") for i in range(10)]
    add(conn, pdf("b.pdf", clash), 2)
    result = build_bundle(conn, "reyna", tmp_path, max_conflict_share=0.05)
    assert result.status == "building" and len(result.conflicts) == 10


def test_conflicts_of_exactly_the_allowed_share_are_tolerated(conn, pdf, tmp_path):
    rows = [(str(15000 + i), f"Song {i}", "Artist") for i in range(100)]
    add(conn, pdf("a.pdf", rows), 1)
    clash = [(str(15000 + i), f"Other {i}", "Other") for i in range(5)]
    add(conn, pdf("b.pdf", clash), 2)
    result = build_bundle(conn, "reyna", tmp_path, max_conflict_share=0.05)
    assert len(result.conflicts) == 5 and result.status == "validated" and result.songs == 95
