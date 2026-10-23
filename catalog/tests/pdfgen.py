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
