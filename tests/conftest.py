from pathlib import Path

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_PDF = ROOT / "docs" / "Greathelm-A4-print-and-cut.pdf"


@pytest.fixture(scope="session")
def example_pdf():
    if not EXAMPLE_PDF.exists():
        pytest.skip("example PDF not present")
    return EXAMPLE_PDF


@pytest.fixture(scope="session")
def quickstart_art(example_pdf, tmp_path_factory):
    """The raw artwork of the example's last sheet (05 / Quickstart Map)."""
    path = tmp_path_factory.mktemp("art") / "quickstart.png"
    with pymupdf.open(example_pdf) as doc:
        page = doc[-1]
        pymupdf.Pixmap(doc, page.get_images()[0][0]).save(path)
    return path
