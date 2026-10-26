"""Text normalization. Raw text is always kept; folded forms are only for matching."""

from __future__ import annotations

import re
import unicodedata

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "`": "'"})
_SPACES = re.compile(r"\s+")
_APOSTROPHES = re.compile(r"['’]")
_NON_ALNUM = re.compile(r"[^0-9a-z]+")


# The publisher prints "v.86" or "v.87" beside songs a volume carries over from an earlier one.
# It is a note about the volume, not part of the title, and can land mid-way in a wrapped title.
_VERSION_MARK = re.compile(r"(?<![A-Za-z0-9])v\.\s?\d{1,3}(?![A-Za-z0-9])")


def strip_version_marks(text: str) -> str:
    """The title without the publisher's lowercase "v.NN" volume marks."""
    return _SPACES.sub(" ", _VERSION_MARK.sub(" ", text)).strip()


def clean(text: str) -> str:
    """Display form: NFKC, straight quotes, single spaces."""
    return _SPACES.sub(" ", unicodedata.normalize("NFKC", text).translate(_QUOTES)).strip()


def fold(text: str) -> str:
    """Matching form: no accents or case, apostrophes dropped, other punctuation is a space."""
    decomposed = unicodedata.normalize("NFKD", clean(text))
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    lowered = _APOSTROPHES.sub("", stripped.casefold()).replace("&", " and ")
    return _NON_ALNUM.sub(" ", lowered).strip()
