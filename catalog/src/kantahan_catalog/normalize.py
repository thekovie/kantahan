"""Text normalization. Raw text is always kept; folded forms are only for matching."""

from __future__ import annotations

import re
import unicodedata

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "`": "'"})
_SPACES = re.compile(r"\s+")
_APOSTROPHES = re.compile(r"['’]")
_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def clean(text: str) -> str:
    """Display form: NFKC, straight quotes, single spaces."""
    return _SPACES.sub(" ", unicodedata.normalize("NFKC", text).translate(_QUOTES)).strip()


def fold(text: str) -> str:
    """Matching form: no accents or case, apostrophes dropped, other punctuation is a space."""
    decomposed = unicodedata.normalize("NFKD", clean(text))
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    lowered = _APOSTROPHES.sub("", stripped.casefold()).replace("&", " and ")
    return _NON_ALNUM.sub(" ", lowered).strip()
