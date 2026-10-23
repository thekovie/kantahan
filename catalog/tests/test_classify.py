import pytest

from kantahan_catalog.classify import FAMILY_TO_MODEL, classify_header


@pytest.mark.parametrize(
    ("lines", "family"),
    [
        (["Vol. 62 For Reyna ! 1"], "reyna"),
        (["Vol. 66 For Reyna DVD ! 1"], "reyna"),
        (["Reyna Vol. 63! 1"], "reyna"),
        (["Vol. 80 T-X-R-BMB Series ! 1"], "t-x-r-bmb"),
        (["! Vol 98 T-X Series"], "t-x"),
        (["T-X series Vol. 108", "KBox Vol. 35"], "t-x"),
        (["Volume 95", "SD SERIES featuring songs New Songs"], "sd-series"),
        (["! Volume 85"], "unstated"),
        ([], "unstated"),
    ],
)
def test_family_comes_from_header_text(lines, family):
    assert classify_header(lines).family == family


def test_evidence_is_the_matching_header_line():
    result = classify_header(["platinumkaraoke.ph", " Vol. 62 For Reyna ! 1 "])
    assert result.evidence == "Vol. 62 For Reyna ! 1"


def test_only_reyna_family_maps_to_a_model():
    assert FAMILY_TO_MODEL == {"reyna": "reyna"}


def test_negated_reyna_is_not_reyna():
    assert classify_header(["Not for Reyna"]).family == "unstated"


def test_song_rows_following_a_short_header_are_not_read_as_header():
    lines = ["Volume 85", "Dahilan 15572 For Reyna Callalily"]
    assert classify_header(lines).family == "unstated"
