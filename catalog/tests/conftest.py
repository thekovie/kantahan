import pytest
from pdfgen import make_pdf

from kantahan_catalog import db
from kantahan_catalog.importer import ensure_source


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.migrate(c)
    ensure_source(c, "a", "https://example.test/a", "P0")
    ensure_source(c, "b", "https://example.test/b", "P0")
    yield c
    c.close()


@pytest.fixture
def pdf(tmp_path):
    """Build a one-page PDF from a list of (number, title, artist) rows."""

    def build(name, rows, header="Vol. 1 For Reyna ! 1"):
        chunks = [rows[i : i + 40] for i in range(0, len(rows), 40)] or [[]]
        return make_pdf(tmp_path / name, [[chunk] for chunk in chunks], header=header)

    return build


def sample_rows(start=15000, count=6, prefix="Song"):
    return [(f"{start + i}", f"{prefix} {i}", f"Artist {i}") for i in range(count)]
