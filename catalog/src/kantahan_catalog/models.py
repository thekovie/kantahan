"""Immutable value types shared across the pipeline."""

from __future__ import annotations

from dataclasses import dataclass


class ExtractionError(Exception):
    """The document structure is not what the extractor understands."""


@dataclass(frozen=True)
class RawRow:
    """One song row as printed in a source document. Numbers stay strings."""

    number: str
    title: str
    artist: str
    page: int
    table: int
    row: int
    flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class DocumentExtract:
    rows: tuple[RawRow, ...]
    pages: int
    header_lines: tuple[str, ...]
    stray_tokens: int  # number-like tokens found outside any number cell


@dataclass(frozen=True)
class Classification:
    family: str  # reyna | t-x-r-bmb | t-x | sd-series | unstated
    evidence: str  # the header line that justified the family, "" when unstated


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str  # "error" quarantines the document, "warn" is recorded only
    message: str
    number: str | None = None
