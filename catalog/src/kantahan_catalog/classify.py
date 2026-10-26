"""Classify a document by what its own header says, never by where it was listed."""

from __future__ import annotations

import re
from collections.abc import Iterable

from .models import Classification

# Order matters: the longer family name must be tested before its prefix.
_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("t-series-hdd", re.compile(r"\bT-Series,?\s+HDD\b", re.I)),
    ("t-x-r-bmb", re.compile(r"T-X-R-BMB", re.I)),
    ("t-x", re.compile(r"\bT-X\b", re.I)),
    ("sd-series", re.compile(r"\bSD SERIES\b", re.I)),
    ("reyna", re.compile(r"(?<!not )(?<!non-)\bfor reyna\b|\breyna vol\b", re.I)),
)

_SONG_ROW = re.compile(r"\b\d{5}\b", re.ASCII)

# Families whose documents are evidence for a model in our database.
# Only what the audit verified: headers saying "For Reyna" prove the Reyna family,
# not which Reyna variant (see docs/model-compatibility.md).
FAMILY_TO_MODEL: dict[str, str] = {"reyna": "reyna"}


def classify_header(lines: Iterable[str]) -> Classification:
    for line in lines:
        if _SONG_ROW.search(line):
            continue  # header scan must not read song rows that follow a short header
        for family, pattern in _RULES:
            if pattern.search(line):
                return Classification(family=family, evidence=line.strip())
    return Classification(family="unstated", evidence="")
