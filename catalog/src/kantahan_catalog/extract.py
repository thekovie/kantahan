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
# Normal wrapped lines never overlap (line pitch exceeds glyph height), so even a small overlap
# means two cells are drawn on top of each other.
OVERLAP_FRACTION = 0.05
BOUNDARY_REACH = 0.6  # an overlap must sit this close (in row pitches) to a row boundary
SAME_LINE = 0.3

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


# A long word that wraps mid-word leaves one lowercase letter on the next line. "x" is excluded:
# it is a real separator ("A x B").
_WORD_TAIL = re.compile(r"[a-wyz]", re.ASCII)


def _lines_text(words: list[dict[str, Any]]) -> str:
    """Join words top to bottom, left to right; stacked wrapped lines stay separate."""
    lines: list[list[dict[str, Any]]] = []
    for w in sorted(words, key=lambda w: w["top"]):
        if lines and w["top"] - lines[-1][0]["top"] <= 0.5 * (w["bottom"] - w["top"]):
            lines[-1].append(w)
        else:
            lines.append([w])
    text = ""
    for line in lines:
        line_text = " ".join(w["text"] for w in sorted(line, key=lambda w: w["x0"]))
        glue = "" if text and _WORD_TAIL.fullmatch(line_text) else " "
        text += (glue if text else "") + line_text
    return clean(text)


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


def _x_overlap(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return bool(min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]) > 0)


def _nearest_row(word: dict[str, Any], cy: list[float], pitch: float) -> int | None:
    y = _center(word)[1]
    row = min(range(len(cy)), key=lambda k: abs(cy[k] - y))
    return row if abs(cy[row] - y) <= pitch * ROW_REACH else None


def _assign_cell(
    words: list[dict[str, Any]], cy: list[float], pitch: float
) -> tuple[dict[int, list[dict[str, Any]]], set[int]]:
    """Give each word of one cell column to a row. Returns (row -> words, unresolved rows).

    Text that overflows its row is drawn over the neighbour's text. Two words that overlap
    cannot be in the same cell, and the PDF writes cells row by row, so of such a pair the
    word written first belongs to the row above the nearest row boundary and the later one to
    the row below it. Words on the same text line that do not overlap horizontally belong to
    the same cell. Anything still ambiguous is returned as unresolved.
    """
    row_of = {id(w): _nearest_row(w, cy, pitch) for w in words}
    placed = [w for w in words if row_of[id(w)] is not None]
    forced: dict[int, int] = {}
    unresolved: set[int] = set()
    pairs = [
        (a, b) if a["_i"] < b["_i"] else (b, a)
        for i, a in enumerate(placed)
        for b in placed[i + 1 :]
        if _overlapping(a, b)
    ]
    for first, second in sorted(pairs, key=lambda p: (p[1]["_i"], p[0]["_i"])):
        mid = (_center(first)[1] + _center(second)[1]) / 2
        boundary = min(
            range(len(cy) - 1), key=lambda j: abs((cy[j] + cy[j + 1]) / 2 - mid), default=None
        )
        origin = {row_of[id(first)], row_of[id(second)]}
        if (
            boundary is None
            or abs((cy[boundary] + cy[boundary + 1]) / 2 - mid) > pitch * BOUNDARY_REACH
        ):
            unresolved |= {r for r in origin if r is not None}
            continue
        for word, row in ((first, boundary), (second, boundary + 1)):
            if forced.setdefault(id(word), row) != row:
                unresolved |= {row, forced[id(word)]}
    for _ in range(2):
        for w in placed:
            if id(w) in forced:
                continue
            mates = {
                forced[id(f)]
                for f in placed
                if id(f) in forced
                and abs(f["top"] - w["top"]) <= SAME_LINE * (w["bottom"] - w["top"])
                and not _x_overlap(f, w)
            }
            if len(mates) == 1:
                forced[id(w)] = mates.pop()
    cells: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for w in placed:
        cells[forced.get(id(w), row_of[id(w)] or 0)].append(w)
    for row, row_words in cells.items():
        if any(_overlapping(a, b) for i, a in enumerate(row_words) for b in row_words[i + 1 :]):
            unresolved.add(row)
    return cells, unresolved


def _suspect(unresolved: set[int], row_count: int) -> set[int]:
    """An unresolved overlap makes its rows and their neighbours uncertain."""
    out = set(unresolved)
    for row in unresolved:
        out.update(r for r in (row - 1, row + 1) if 0 <= r < row_count)
    return out


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
    title_words, artist_words = [], []
    for w in words:
        x = _center(w)[0]
        if NUMBER_CELL.fullmatch(w["text"]) and e1 - 3 <= x <= e2 + 3:
            continue
        if e0 - 3 <= x <= e1:
            title_words.append(w)
        elif e2 < x <= e3 + 3:
            artist_words.append(w)
    titles, title_open = _assign_cell(title_words, cy, pitch)
    artists, artist_open = _assign_cell(artist_words, cy, pitch)
    title_hits = _suspect(title_open, len(numbers))
    artist_hits = _suspect(artist_open, len(numbers))
    rows = []
    for i, n in enumerate(numbers):
        flags = (("overprint",) if i in artist_hits else ()) + (
            ("title_overprint",) if i in title_hits else ()
        )
        rows.append(
            RawRow(
                number=n["text"],
                title=_lines_text(titles.get(i, [])),
                artist=_lines_text(artists.get(i, [])),
                page=page_no,
                table=table_no,
                row=i,
                flags=flags,
            )
        )
    return rows, len(numbers)


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
                for position, word in enumerate(words):
                    word["_i"] = position  # PDF write order
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
