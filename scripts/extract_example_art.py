"""Extract the map artwork from the Greathelm print-and-cut PDF.

Usage: uv run python scripts/extract_example_art.py [PDF] [OUT_DIR]
Writes one PNG per map sheet (e.g. 05-quickstart-map.png), unrotated.
"""

import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent


def extract(pdf: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with pymupdf.open(pdf) as doc:
        for page in doc:
            images = page.get_images(full=True)
            if not images:
                continue
            title = next((line for line in page.get_text().splitlines() if re.match(r"\d+ / ", line)), f"page-{page.number + 1}")
            name = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            path = out_dir / f"{name}.png"
            pymupdf.Pixmap(doc, images[0][0]).save(path)
            written.append(path)
    return written


if __name__ == "__main__":
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs/Greathelm-A4-print-and-cut.pdf"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "examples/art"
    for p in extract(pdf, out):
        print(p)
