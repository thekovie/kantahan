"""Extract song rows from a song-list PDF using table geometry, not reading order.

The audited documents draw three tables per page. Each table has four vertical cell
borders: [title+icon | number | artist]. Words are assigned to the number whose row
they sit closest to. Reading-order text interleaves the columns and must not be used.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pdfplumber

from .models import DocumentExtract, ExtractionError, RawRow
from .normalize import clean, strip_version_marks

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
# A column header ("Song Title", "Popularized By:") sits 0.8 to 0.9 of a row away from the row under
# it, which is inside ROW_REACH, so its words were read as part of that row. It appears above the
# first row and again at the start of each section inside a table. Header words that far from every
# row (a wrapped three-line title reaches only about 0.55) are dropped. Position alone is not
# enough: a tall wrapped title can legitimately reach that far, so only the header's own words go.
HEADER_REACH = 0.6
HEADER_WORDS = frozenset({"song", "title", "popularized", "by", "by:"})
# Two cells drawn on top of each other overlap heavily (measured 0.8 of a word's area), while the
# tightly spaced lines of one wrapped title overlap by about 0.16 and must stay together.
OVERLAP_FRACTION = 0.35
BOUNDARY_REACH = 0.6  # an overlap must sit this close (in row pitches) to a row boundary
SAME_LINE = 0.3

# A border-based reading is not trusted when more codes than this are left outside every table:
# the document is then read by where its codes sit instead (see borderless_template).
FALLBACK_STRAYS = 3
FALLBACK_STRAY_RATE = 0.01
CODE_CLUSTER_GAP = 12.0  # points between code columns of different tables
MIN_CODE_SHARE = 0.05  # a code column holds at least this share of all 5-digit tokens
MIN_CELL_GAP = 8.0  # empty space between an artist cell's text and the next table's titles
MERGED_MIN_ROWS = 1.8  # a cell this many row pitches tall spans several rows
MERGED_MIN_WIDTH = 20.0
ZONE_PAD = 3.0  # _table_rows accepts words this far outside a table's title and artist edges
MIN_PAGE_CODES = 3  # codes per column a page needs before its own columns are trusted
MIN_PAGE_VOTES = 3  # lines a page needs before its own cut is trusted over the document's
LINE_TOLERANCE = 4.0  # words whose centres are this close vertically are on one text line

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


def _code_columns(pages: list[Any], min_count: int = 5) -> list[tuple[float, float]]:
    """x-ranges of the columns that hold the 5-digit song codes, left to right."""
    spans = sorted(
        (w["x0"], w["x1"])
        for page in pages
        for w in page.extract_words(x_tolerance=1.5, y_tolerance=2)
        if STRAY_TOKEN.fullmatch(w["text"])
    )
    clusters: list[list[tuple[float, float]]] = []
    for span in spans:
        if clusters and span[0] - clusters[-1][-1][0] <= CODE_CLUSTER_GAP:
            clusters[-1].append(span)
        else:
            clusters.append([span])
    keep = [c for c in clusters if len(c) >= max(min_count, MIN_CODE_SHARE * len(spans))]
    return [(min(a for a, _ in c), max(b for _, b in c)) for c in keep]


def _cut_votes(page: Any, low: float, high: float) -> Counter[int]:
    """Where, on each text line of this page between two code columns, the widest gap ends.

    That gap is the cell boundary: artist text on its left, the next table's title on its
    right. Titles are left-aligned, so most lines vote for the same x.
    """
    words = sorted(
        (w for w in page.extract_words(x_tolerance=1.5, y_tolerance=2) if low <= w["x0"] <= high),
        key=lambda w: (_center(w)[1], w["x0"]),
    )
    lines: list[list[dict[str, Any]]] = []
    for w in words:
        if lines and _center(w)[1] - _center(lines[-1][0])[1] <= LINE_TOLERANCE:
            lines[-1].append(w)
        else:
            lines.append([w])
    votes: Counter[int] = Counter()
    for line in lines:
        line.sort(key=lambda w: w["x0"])
        gaps = [(b["x0"] - a["x1"], b["x0"]) for a, b in zip(line, line[1:], strict=False)]
        if gaps and max(gaps)[0] >= MIN_CELL_GAP:
            votes[round(max(gaps)[1])] += 1
    return votes


def _borrow(index: int, measured: dict[int, Any]) -> Any:
    """The measurement of the nearest page that has one, preferring the same side of the spread.

    Some documents alternate page offsets (book-style inner margins), so a sparse page is most
    like another page an even number of pages away.
    """
    best = min(measured, key=lambda j: (abs(index - j) % 2, abs(index - j)))
    return measured[best]


def _majority_cut(votes: Counter[int]) -> float | None:
    """The cut a page's text lines agree on, or None when they do not agree (or are too few)."""
    total = sum(votes.values())
    if total < MIN_PAGE_VOTES:
        return None
    x, n = votes.most_common(1)[0]
    return float(x) - 1.5 if n * 2 >= total else None


def borderless_template(pages: list[Any]) -> list[list[Edges]]:
    """Table edges per page for documents whose cell borders cannot be read as borders.

    Each table has one code column. A table's titles run from the previous table's cut to its
    codes, its artists from its codes to the next cut. Pages of one document are laid out with
    slightly different offsets, so code columns and cuts are measured on each page; a page with
    too little to measure borrows from a similar page.
    """
    per_page = [_code_columns([page], MIN_PAGE_CODES) for page in pages]
    counts = Counter(len(c) for c in per_page if c)
    expected = counts.most_common(1)[0][0] if counts else 0
    if expected < 2:
        raise ExtractionError("expected at least two code columns")
    measured = {i: c for i, c in enumerate(per_page) if len(c) == expected}
    columns = [measured[i] if i in measured else _borrow(i, measured) for i in range(len(pages))]

    spans = [
        [(cols[k][1] + 2, cols[k + 1][0] - 2) for k in range(expected - 1)] for cols in columns
    ]
    votes = [
        [_cut_votes(page, lo, hi) for lo, hi in page_spans]
        for page, page_spans in zip(pages, spans, strict=True)
    ]
    own: list[list[float | None]] = [[_majority_cut(v) for v in page_votes] for page_votes in votes]
    cuts_per_page = []
    for i in range(len(pages)):
        row: list[float] = []
        for k in range(expected - 1):
            have: dict[int, float] = {
                j: c for j in range(len(pages)) if (c := own[j][k]) is not None
            }
            if not have:
                raise ExtractionError("cannot tell where one table ends and the next begins")
            chosen = own[i][k]
            row.append(chosen if chosen is not None else float(_borrow(i, have)))
        cuts_per_page.append(row)
    page_width = min(float(p.width) for p in pages)
    templates: list[list[Edges]] = []
    for i, cols in enumerate(columns):
        bounded = [
            min(max(float(c), lo), hi)
            for c, (lo, hi) in zip(cuts_per_page[i], spans[i], strict=True)
        ]
        # A word counts for a table when its centre lies within 3 points of the table's edges
        # (see _table_rows); the cut therefore sits between the two zones with no overlap.
        edges = [0.0, *bounded, page_width]
        last = len(cols) - 1
        templates.append(
            [
                (
                    edges[k] + (ZONE_PAD if k else 0.0),
                    c[0] - 1,
                    c[1] + 1,
                    edges[k + 1] - (ZONE_PAD + 0.01 if k < last else 0.0),
                )
                for k, c in enumerate(cols)
            ]
        )
    return templates


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


def _line_count(words: list[dict[str, Any]]) -> int:
    lines: list[float] = []
    for w in sorted(words, key=lambda w: w["top"]):
        if not lines or w["top"] - lines[-1] > 0.5 * (w["bottom"] - w["top"]):
            lines.append(w["top"])
    return len(lines)


def _merged_artists(
    artist_words: list[dict[str, Any]],
    cy: list[float],
    pitch: float,
    edges: Edges,
    rects: list[dict[str, Any]],
) -> dict[int, str]:
    """Artist text of cells that are drawn across several rows ("5 songs by one artist").

    Such a cell is a tall rectangle in the artist column. Its text belongs to every row whose
    number sits inside it, not just to the row the text happens to be centred on.
    """
    out: dict[int, str] = {}
    for r in rects:
        if not (
            r["x0"] >= edges[2] - 3
            and r["x1"] <= edges[3] + 6
            and r["x1"] - r["x0"] >= MERGED_MIN_WIDTH
            and r["bottom"] - r["top"] >= MERGED_MIN_ROWS * pitch
        ):
            continue
        inside = [
            w
            for w in artist_words
            if r["x0"] <= _center(w)[0] <= r["x1"] and r["top"] <= _center(w)[1] <= r["bottom"]
        ]
        text = _lines_text(inside)
        covered = [row for row, y in enumerate(cy) if r["top"] <= y <= r["bottom"]]
        # A merged cell holds one short text for several rows. If it has about a line per row
        # it is a background shape behind ordinary cells, not a merged cell.
        if not text or len(covered) < 2 or _line_count(inside) >= len(covered):
            continue
        for row in covered:
            out[row] = text
    return out


def _table_rows(
    words: list[dict[str, Any]],
    edges: Edges,
    page_no: int,
    table_no: int,
    rects: list[dict[str, Any]] | None = None,
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
        x, y = _center(w)
        if w["text"].lower() in HEADER_WORDS and min(abs(c - y) for c in cy) > pitch * HEADER_REACH:
            continue  # a column header, not part of any row
        if NUMBER_CELL.fullmatch(w["text"]) and e1 - 3 <= x <= e2 + 3:
            continue
        if e0 - 3 <= x <= e1:
            title_words.append(w)
        elif e2 < x <= e3 + 3:
            artist_words.append(w)
    titles, title_open = _assign_cell(title_words, cy, pitch)
    artists, artist_open = _assign_cell(artist_words, cy, pitch)
    merged = _merged_artists(artist_words, cy, pitch, edges, rects or [])
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
                title=strip_version_marks(_lines_text(titles.get(i, []))),
                artist=merged.get(i) or _lines_text(artists.get(i, [])),
                page=page_no,
                table=table_no,
                row=i,
                flags=flags,
            )
        )
    return rows, len(numbers)


def _read(pages: list[Any], templates: list[list[Edges]]) -> tuple[list[RawRow], int]:
    rows: list[RawRow] = []
    used = stray = 0
    for page_no, page in enumerate(pages, start=1):
        words = page.extract_words(x_tolerance=1.5, y_tolerance=2, use_text_flow=True)
        for position, word in enumerate(words):
            word["_i"] = position  # PDF write order
        page_used = 0
        for table_no, edges in enumerate(templates[page_no - 1]):
            table_rows, count = _table_rows(words, edges, page_no, table_no, page.rects)
            rows.extend(table_rows)
            page_used += count
        used += page_used
        tokens = sum(1 for w in words if STRAY_TOKEN.fullmatch(w["text"]))
        stray += max(tokens - page_used, 0)
    return rows, max(stray, 0)


def _trusted(rows: list[RawRow], stray: int) -> bool:
    """True when the validator would not reject this reading for stray codes."""
    return stray <= FALLBACK_STRAYS and (stray <= 1 or stray <= FALLBACK_STRAY_RATE * len(rows))


def extract_rows(path: str | Path) -> DocumentExtract:
    """Extract all song rows. Raises ExtractionError when the structure is not understood.

    Documents are read through their cell borders first (the audited Reyna generation). When that
    leaves many codes outside every table, or finds no usable structure, the codes' own positions
    are used instead, and whichever reading leaves fewer stray codes wins.
    """
    try:
        with pdfplumber.open(str(path)) as pdf:
            if len(pdf.pages) > MAX_PAGES:
                raise ExtractionError(f"document has {len(pdf.pages)} pages (limit {MAX_PAGES})")
            pages = list(pdf.pages)
            if not pages:
                raise ExtractionError("document has no pages")
            best: tuple[list[RawRow], int] | None = None
            failure: ExtractionError | None = None
            readers: tuple[Callable[[], list[list[Edges]]], ...] = (
                lambda: [table_template(pages)] * len(pages),
                lambda: borderless_template(pages),
            )
            for templates_for in readers:
                try:
                    candidate = _read(pages, templates_for())
                except ExtractionError as exc:
                    failure = failure or exc
                    continue
                if best is None or (candidate[1] < best[1] and candidate[0]):
                    best = candidate
                if _trusted(*best):
                    break
            if best is None:
                raise failure or ExtractionError("no readable table structure")
            return DocumentExtract(tuple(best[0]), len(pages), _header_lines(pages[0]), best[1])
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
