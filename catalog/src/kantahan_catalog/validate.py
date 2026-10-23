"""Document validation. Errors quarantine a document; warnings are recorded and surfaced."""

from __future__ import annotations

import re
import statistics

from .models import DocumentExtract, Issue

NUMBER_FORMAT = re.compile(r"\d{5}", re.ASCII)  # observed in all audited documents; zeros allowed
MAX_MISSING_ARTIST_RATE = 0.05
MAX_ROW_DROP = 0.02  # vs the previous parse of the same link
RANGE_WINDOW = 450  # numbers further than this from the median are flagged for review
SAMPLE = 5
# Number-like tokens outside every table mean rows may have been missed. The audited documents
# have at most one (page furniture), so tolerate a handful and block beyond that.
MAX_STRAY_TOKENS = 3
MAX_STRAY_RATE = 0.01


def validate_document(
    extract: DocumentExtract, previous_rows: int | None = None, blank_artists_ok: bool = False
) -> list[Issue]:
    rows = extract.rows
    if not rows:
        return [Issue("no_rows", "error", "no song rows were extracted")]
    issues: list[Issue] = []
    issues += _row_errors(extract)
    issues += _duplicates(extract)
    issues += _artist_checks(extract, blank_artists_ok)
    issues += _drift(extract, previous_rows)
    issues += _review_flags(extract)
    return issues


def _row_errors(extract: DocumentExtract) -> list[Issue]:
    issues = []
    for r in extract.rows:
        if not NUMBER_FORMAT.fullmatch(r.number):
            issues.append(
                Issue("bad_number", "error", f"unexpected number format {r.number!r}", r.number)
            )
        if not r.title:
            issues.append(Issue("missing_title", "error", f"row {r.number} has no title", r.number))
    return issues


def _duplicates(extract: DocumentExtract) -> list[Issue]:
    seen: dict[str, tuple[str, str]] = {}
    issues = []
    for r in extract.rows:
        if r.number not in seen:
            seen[r.number] = (r.title, r.artist)
        elif seen[r.number] == (r.title, r.artist):
            issues.append(
                Issue("duplicate_identical", "warn", f"{r.number} listed twice", r.number)
            )
        else:
            issues.append(
                Issue(
                    "duplicate_conflict",
                    "error",
                    f"{r.number} listed twice with different text",
                    r.number,
                )
            )
    return issues


def _artist_checks(extract: DocumentExtract, blank_artists_ok: bool = False) -> list[Issue]:
    rows = extract.rows
    missing = [r for r in rows if not r.artist]
    issues = []
    if len(missing) / len(rows) > MAX_MISSING_ARTIST_RATE and not blank_artists_ok:
        issues.append(
            Issue(
                "artist_missing_rate", "error", f"{len(missing)} of {len(rows)} rows have no artist"
            )
        )
    elif missing:
        issues.append(Issue("missing_artist", "warn", f"{len(missing)} rows have no artist"))
    titles = [r for r in rows if "title_overprint" in r.flags]
    if titles:
        issues.append(
            Issue(
                "title_uncertain",
                "warn",
                f"{len(titles)} rows have overprinted title text; rows left out of builds",
            )
        )
    uncertain = [r for r in rows if "overprint" in r.flags]
    if uncertain:
        issues.append(
            Issue(
                "artist_uncertain",
                "warn",
                f"{len(uncertain)} rows have overprinted artist text; artist withheld",
            )
        )
    return issues


def _drift(extract: DocumentExtract, previous_rows: int | None) -> list[Issue]:
    if previous_rows and len(extract.rows) < previous_rows * (1 - MAX_ROW_DROP):
        return [
            Issue(
                "row_drop",
                "error",
                f"{len(extract.rows)} rows now vs {previous_rows} before "
                f"(over {MAX_ROW_DROP:.0%} drop)",
            )
        ]
    return []


def _review_flags(extract: DocumentExtract) -> list[Issue]:
    issues = []
    if extract.stray_tokens:
        # One stray token is audited page furniture and always tolerated.
        too_many = extract.stray_tokens > MAX_STRAY_TOKENS or (
            extract.stray_tokens > 1 and extract.stray_tokens > MAX_STRAY_RATE * len(extract.rows)
        )
        issues.append(
            Issue(
                "stray_tokens",
                "error" if too_many else "warn",
                f"{extract.stray_tokens} number-like tokens outside tables"
                + (" (rows may be missing)" if too_many else ""),
            )
        )
    numeric = [int(r.number) for r in extract.rows if r.number.isdigit()]
    if numeric:
        median = statistics.median(numeric)
        outliers = sorted(n for n in numeric if abs(n - median) > RANGE_WINDOW)
        if outliers:
            issues.append(
                Issue(
                    "range_outlier",
                    "warn",
                    f"{len(outliers)} numbers far from the volume's main block "
                    f"(sample {outliers[:SAMPLE]})",
                )
            )
    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(i.severity == "error" for i in issues)
