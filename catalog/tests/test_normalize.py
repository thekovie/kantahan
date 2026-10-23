from kantahan_catalog.normalize import clean, fold


def test_clean_collapses_spaces_and_straightens_quotes():
    assert clean("  Ako’y   Iyong-Iyo \n") == "Ako'y Iyong-Iyo"


def test_fold_is_case_and_accent_insensitive():
    assert fold("Niño CAFÉ") == fold("nino cafe") == "nino cafe"


def test_fold_drops_apostrophes_so_contractions_match():
    assert fold("Ako'y Para Sa'yo") == "akoy para sayo"


def test_fold_turns_other_punctuation_into_spaces_and_expands_ampersand():
    assert fold("Chit-Chirit-Chit") == "chit chirit chit"
    assert fold("England Dan & John Ford Coley") == "england dan and john ford coley"


def test_fold_keeps_digits_and_never_returns_none():
    assert fold("24/7, 365") == "24 7 365"
    assert fold("") == ""
