"""Extract song rows from a song-list PDF using table geometry, not reading order.

The audited documents draw three tables per page. Each table has four vertical cell
borders: [title+icon | number | artist]. Words are assigned to the number whose row
they sit closest to. Reading-order text interleaves the columns and must not be used.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pdfplumber

from .models import DocumentExtract, ExtractionError, RawRow
from .normalize import clean

# ASCII digits only and fullmatch: `\d` alone would accept fullwidth digits, `$` a trailing newline.
NUMBER_CELL = re.compile(r"\d{3,7}", re.ASCII)  # number-like in a number cell; validate decides
STRAY_TOKEN = re.compile(r"\d{5}", re.ASCII)
MAX_PAGES = 40  # audited documents have 1 to 6 pages
MAX_ROW_WIDTH_SLACK = 1.0
# Every border in the 43 audited Reyna-section documents is seen on 10+ rows, so any border at
# all counts. Noise would break the multiple-of-4 check and quarantine the document.
MIN_EDGE_ROWS = 1
EDGE_MERGE = 1.5  # points; borders closer than this are the same border
HEADER_LINES = 12
DEFAULT_PITCH = 20.0
ROW_REACH = 0.9  # a word further than this many pitches from a number is not in its row
OVERLAP_FRACTION = 0.3

Edges = tuple[float, float, float, float]


def _vertical_borders(page: Any) -> Iterator[float]:
    for obj in (*page.rects, *page.lines):
        height = obj["bottom"] - obj["top"]
        if abs(obj["x1"] - obj["x0"]) < EDGE_MERGE and 8 < height < 45:
            yield (obj["x0"] + obj["x1"]) / 2


def table_template(pages: list[Any]) -> list[Edges]:
    """Find the table borders shared by all pages of a document."""
    xs = sorted(round(x, 1) for page in pages for x in _vertical_borders(page))
    clusters: list[list[float]] = []
    for x in xs:
        if clusters and x - clusters[-1][-1] <= EDGE_MERGE:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    edges = [statistics.fmean(c) for c in clusters if len(c) >= MIN_EDGE_ROWS]
    if len(edges) % 4 == 3 and len(edges) >= 7:
        # Some generations leave the last table without a right border: reuse the artist cell
        # width of the complete tables (audited: Vol 89, 94, 98 to 100). The guess must stay on
        # the page, otherwise the structure is not understood.
        widths = [edges[i + 3] - edges[i + 2] for i in range(0, len(edges) - 3, 4)]
        guessed = edges[-1] + statistics.median(widths)
        if guessed > min(float(p.width) for p in pages) + MAX_ROW_WIDTH_SLACK:
            raise ExtractionError("last table border would fall outside the page")
        edges.append(guessed)
    if not edges or len(edges) % 4:
        raise ExtractionError(f"unexpected table structure: {len(edges)} vertical borders")
    return [(edges[i], edges[i + 1], edges[i + 2], edges[i + 3]) for i in range(0, len(edges), 4)]


def _center(word: dict[str, Any]) -> tuple[float, float]:
    return (word["x0"] + word["x1"]) / 2, (word["top"] + word["bottom"]) / 2


def _lines_text(words: list[dict[str, Any]]) -> str:
    """Join words top to bottom, left to right; stacked wrapped lines stay separate."""
    lines: list[list[dict[str, Any]]] = []
    for w in sorted(words, key=lambda w: w["top"]):
        if lines and w["top"] - lines[-1][0]["top"] <= 0.5 * (w["bottom"] - w["top"]):
            lines[-1].append(w)
        else:
            lines.append([w])
    return clean(" ".join(w["text"] for ln in lines for w in sorted(ln, key=lambda w: w["x0"])))


def _overlapping(a: dict[str, Any], b: dict[str, Any]) -> bool:
    dx = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
    dy = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
    if dx <= 0 or dy <= 0:
        return False
    smaller = min(
        (a["x1"] - a["x0"]) * (a["bottom"] - a["top"]),
        (b["x1"] - b["x0"]) * (b["bottom"] - b["top"]),
    )
    return bool(dx * dy > OVERLAP_FRACTION * smaller)


def _table_rows(
    words: list[dict[str, Any]], edges: Edges, page_no: int, table_no: int
) -> tuple[list[RawRow], int]:
    e0, e1, e2, e3 = edges
    numbers = sorted(
        (
            w
            for w in words
            if NUMBER_CELL.fullmatch(w["text"]) and e1 - 3 <= _center(w)[0] <= e2 + 3
        ),
        key=lambda w: w["top"],
    )
    if not numbers:
        return [], 0
    cy = [_center(w)[1] for w in numbers]
    pitch = (
        statistics.median(b - a for a, b in zip(cy, cy[1:], strict=False))
        if len(cy) > 1
        else DEFAULT_PITCH
    )
    cells: dict[str, dict[int, list[dict[str, Any]]]] = {
        "title": defaultdict(list),
        "artist": defaultdict(list),
    }
    for w in words:
        x, y = _center(w)
        kind = "title" if e0 - 3 <= x <= e1 else "artist" if e2 < x <= e3 + 3 else ""
        if not kind:
            continue
        nearest = min(range(len(cy)), key=lambda k: abs(cy[k] - y))
        if abs(cy[nearest] - y) <= pitch * ROW_REACH:
            cells[kind][nearest].append(w)
    artist_hits = _overprinted_rows(cells["artist"], len(numbers))
    title_hits = _overprinted_rows(cells["title"], len(numbers))
    rows = []
    for i, n in enumerate(numbers):
        flags = (("overprint",) if i in artist_hits else ()) + (
            ("title_overprint",) if i in title_hits else ()
        )
        rows.append(
            RawRow(
                number=n["text"],
                title=_lines_text(cells["title"][i]),
                artist=_lines_text(cells["artist"][i]),
                page=page_no,
                table=table_no,
                row=i,
                flags=flags,
            )
        )
    return rows, len(numbers)


def _overprinted_rows(cell: dict[int, list[dict[str, Any]]], row_count: int) -> set[int]:
    """Rows whose text overlaps any other word in the same column, plus both neighbours.

    Overflowing text can belong to the row above or below the overlap, so both are suspect.
    """
    tagged = [(row, w) for row, words in cell.items() for w in words]
    hits: set[int] = set()
    for i, (row_a, a) in enumerate(tagged):
        for row_b, b in tagged[i + 1 :]:
            if _overlapping(a, b):
                hits.update({row_a, row_b})
    suspect = set(hits)
    for row in hits:
        suspect.update(r for r in (row - 1, row + 1) if 0 <= r < row_count)
    return suspect


def extract_rows(path: str | Path) -> DocumentExtract:
    """Extract all song rows. Raises ExtractionError when the structure is not understood."""
    try:
        with pdfplumber.open(str(path)) as pdf:
            if len(pdf.pages) > MAX_PAGES:
                raise ExtractionError(f"document has {len(pdf.pages)} pages (limit {MAX_PAGES})")
            pages = list(pdf.pages)
            if not pages:
                raise ExtractionError("document has no pages")
            template = table_template(pages)
            rows: list[RawRow] = []
            used = stray = 0
            for page_no, page in enumerate(pages, start=1):
                words = page.extract_words(x_tolerance=1.5, y_tolerance=2, use_text_flow=True)
                page_used = 0
                for table_no, edges in enumerate(template):
                    table_rows, count = _table_rows(words, edges, page_no, table_no)
                    rows.extend(table_rows)
                    page_used += count
                used += page_used
                tokens = sum(1 for w in words if STRAY_TOKEN.fullmatch(w["text"]))
                stray += max(tokens - page_used, 0)
            header = _header_lines(pages[0])
            return DocumentExtract(tuple(rows), len(pages), header, max(stray, 0))
    except ExtractionError:
        raise
    except Exception as exc:  # corrupt or encrypted PDFs surface as many library errors
        raise ExtractionError(f"cannot read document: {exc}") from exc


def _header_lines(page: Any) -> tuple[str, ...]:
    text = page.extract_text() or ""
    lines = [clean(ln) for ln in text.splitlines() if ln.strip()]
    return tuple(lines[:HEADER_LINES])


def number_counts(rows: tuple[RawRow, ...]) -> Counter[str]:
    return Counter(r.number for r in rows)
