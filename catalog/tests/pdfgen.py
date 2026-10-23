"""Generate synthetic PDFs that mimic the audited song-list layout.

Layout (from the M0 audit): up to three tables side by side per page; each row is
Title | icon | number | artist, drawn with per-row vertical cell borders. Artists use a
small font and wrap over several lines. No real catalog data is used anywhere.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from fpdf import FPDF

# (e0, e1, e2, e3) per table: title+icon cell, number cell, artist cell.
TABLES: tuple[tuple[int, int, int, int], ...] = (
    (14, 117, 159, 204),
    (211, 314, 356, 401),
    (407, 511, 553, 598),
)
TOP = 90
PITCH = 20

Row = tuple[str, str, str]  # number, title, artist
Page = Sequence[Sequence[Row]]  # up to three tables of rows


def _draw_row(pdf: FPDF, edges: tuple[int, int, int, int], y: int, row: Row) -> None:
    number, title, artist = row
    for x in edges:
        pdf.line(x, y, x, y + PITCH)
    pdf.set_font("Helvetica", size=11)
    title_lines = title.split("\n")
    for i, text in enumerate(title_lines):
        pdf.set_xy(edges[0] + 1, y + PITCH / 2 - 5.5 * len(title_lines) + 11 * i)
        pdf.cell(edges[1] - edges[0] - 16, 11, text)
    pdf.set_font("Helvetica", style="B", size=14)
    pdf.set_xy(edges[1] + 1, y + 4)
    pdf.cell(edges[2] - edges[1] - 2, 12, number)
    pdf.set_font("Helvetica", size=7)
    lines = artist.split("\n")
    first = y + PITCH / 2 - 4 * len(lines)
    for i, text in enumerate(lines):
        pdf.set_xy(edges[2] + 1, first + 8 * i)
        pdf.cell(edges[3] - edges[2] - 2, 8, text)


def make_pdf(
    path: Path,
    pages: Sequence[Page],
    header: str = "Vol. 1 For Reyna ! 1",
    stray: str | None = None,
) -> Path:
    """Write a PDF. `artist` strings may contain newlines to force wrapped lines."""
    pdf = FPDF(unit="pt", format="Letter")
    pdf.set_auto_page_break(False)
    for tables in pages:
        pdf.add_page()
        pdf.set_font("Helvetica", size=14)
        pdf.set_xy(20, 30)
        pdf.cell(300, 14, header)
        if stray:
            pdf.set_xy(450, 30)
            pdf.cell(100, 14, stray)
        for edges, rows in zip(TABLES, tables, strict=False):
            for i, row in enumerate(rows):
                _draw_row(pdf, edges, TOP + i * PITCH, row)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))
    return path


# Older song-list layout (audited M4): a small page with two tables side by side, each row
# Title | code in a coloured box | small artist. The page also carries decorative thin
# rectangles at fixed x positions, which look like cell borders but are not table structure.
SMALL_TABLES: tuple[tuple[int, int, int, int], ...] = (
    (20, 120, 161, 190),
    (203, 303, 344, 378),
)
DECOY_X = (9.0, 20.5, 119.2, 130.7, 150.1, 161.6, 186.4, 191.9, 197.9, 203.4, 302.0, 313.6)
SMALL_TOP = 60
SMALL_PITCH = 24


def make_two_table_pdf(path: Path, pages: Sequence[Page], header: str = "Vol. 5 ! 1") -> Path:
    pdf = FPDF(unit="pt", format=(390, 674))
    pdf.set_auto_page_break(False)
    for tables in pages:
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)
        pdf.set_xy(20, 20)
        pdf.cell(200, 12, header)
        for edges, rows in zip(SMALL_TABLES, tables, strict=False):
            pdf.set_font("Helvetica", size=7)
            pdf.set_xy(edges[0], SMALL_TOP - SMALL_PITCH)
            pdf.cell(60, 8, "Title")
            pdf.set_xy(edges[1] + 8, SMALL_TOP - SMALL_PITCH)
            pdf.cell(30, 8, "Code")
            for i, (number, title, artist) in enumerate(rows):
                y = SMALL_TOP + i * SMALL_PITCH
                pdf.set_fill_color(240, 220, 120)
                pdf.rect(edges[1] + 8, y + 2, 32, SMALL_PITCH - 4, style="F")
                pdf.set_font("Helvetica", style="B", size=11)
                pdf.set_xy(edges[1] + 9, y + 6)
                pdf.cell(30, 12, number)
                pdf.set_font("Helvetica", size=10)
                pdf.set_xy(edges[0] + 2, y + 6)
                pdf.cell(edges[1] - edges[0] - 4, 12, title)
                pdf.set_font("Helvetica", size=6)
                lines = artist.split("\n")
                for j, text in enumerate(lines):
                    pdf.set_xy(edges[2] + 2, y + SMALL_PITCH / 2 - 3.5 * len(lines) + 7 * j)
                    pdf.cell(edges[3] - edges[2] - 2, 7, text)
        for i in range(max((len(t) for t in tables), default=0)):
            for x in DECOY_X:
                pdf.rect(x, SMALL_TOP + i * SMALL_PITCH, 0.2, 30, style="F")
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))
    return path
