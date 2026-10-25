"""Lay maps out on sheets and draw them into a PDF."""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
from PIL import Image

from .config import MapSpec
from .geometry import GridLines, HexGrid, Rect, grid_lines

PT = 72 / 25.4  # points per mm

HEADER_SPACE = 20.0  # mm reserved below the top margin, and again above the bottom margin
MARK_GAP = 1.0  # gap between the bleed edge and a crop mark
MARK_LEN = 4.0
MARK_SPACE = MARK_GAP + MARK_LEN
MARK_WIDTH = 0.2
SCALE_BAR = 50.0
JPEG_QUALITY = 92

INSTRUCTIONS = "Print once, single-sided, at 100% / Actual size. Do not fit or shrink."


def fmt(v: float) -> str:
    return f"{round(v, 2):g}"


@dataclass(frozen=True)
class Piece:
    """One sheet's share of a map, in map mm."""

    row: int
    col: int
    rows: int
    cols: int
    cut: Rect  # where this piece is cut; neighbours meet on these lines
    visible: Rect  # what is printed: cut plus bleed, or plus overlap on flap sides

    @property
    def flap_right(self) -> bool:
        return self.col < self.cols - 1

    @property
    def flap_bottom(self) -> bool:
        return self.row < self.rows - 1


@dataclass
class Sheet:
    spec: MapSpec
    piece: Piece
    landscape: bool
    number: int = 0


@dataclass
class MapReport:
    spec: MapSpec
    effective_dpi: float
    pieces: int
    cols: int
    rows: int
    warnings: list[str] = field(default_factory=list)


def page_size(spec: MapSpec, landscape: bool) -> tuple[float, float]:
    w, h = spec.paper.width, spec.paper.height
    return (h, w) if landscape else (w, h)


def map_area(spec: MapSpec, landscape: bool) -> Rect:
    """Page region the visible map (bleed included) may occupy, before marks."""
    pw, ph = page_size(spec, landscape)
    m = spec.margin
    return Rect(m + MARK_SPACE, m + HEADER_SPACE + MARK_SPACE, pw - m - MARK_SPACE, ph - m - HEADER_SPACE - MARK_SPACE)


def split_axis(length: float, avail: float, bleed: float, overlap: float) -> list[float] | None:
    """Cut positions dividing ``length`` into equal pieces that fit ``avail``."""
    if avail <= 0:
        return None
    if length + 2 * bleed <= avail + 1e-9:
        return [0.0, length]
    room = avail - bleed - max(bleed, overlap)
    if room <= 0:
        return None
    n = max(2, math.ceil(length / room - 1e-9))
    return [length * k / n for k in range(n + 1)]


def plan_pieces(spec: MapSpec, landscape: bool) -> list[Piece] | None:
    area = map_area(spec, landscape)
    xs = split_axis(spec.width, area.width, spec.bleed, spec.overlap)
    ys = split_axis(spec.height, area.height, spec.bleed, spec.overlap)
    if xs is None or ys is None:
        return None
    cols, rows = len(xs) - 1, len(ys) - 1
    b, ov = spec.bleed, spec.overlap
    pieces = []
    for r in range(rows):
        for c in range(cols):
            cut = Rect(xs[c], ys[r], xs[c + 1], ys[r + 1])
            visible = Rect(
                cut.x0 - b,
                cut.y0 - b,
                cut.x1 + (ov if c < cols - 1 else b),
                cut.y1 + (ov if r < rows - 1 else b),
            )
            pieces.append(Piece(r, c, rows, cols, cut, visible))
    return pieces


def choose_layout(spec: MapSpec) -> tuple[bool, list[Piece]]:
    """Pick the orientation needing fewest sheets; ties follow the map's shape."""
    options = []
    for landscape in (True, False):
        pieces = plan_pieces(spec, landscape)
        if pieces:
            prefers = landscape == (spec.width >= spec.height)
            options.append((len(pieces), not prefers, landscape, pieces))
    if not options:
        raise ValueError(f"{spec.title}: paper {spec.paper.name} is too small to print anything after margins")
    _, _, landscape, pieces = min(options, key=lambda o: o[:3])
    return landscape, pieces


def prepare_image(spec: MapSpec) -> tuple[Image.Image, float]:
    """Rotate, cover-crop and resample the artwork to the bleed rectangle.

    Returns the image (exactly covering the map plus bleed) and the artwork's
    effective resolution at print size before any downsampling.
    """
    img = Image.open(spec.image)
    img.load()
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        img = Image.new("RGB", rgba.size, (255, 255, 255))
        img.paste(rgba, mask=rgba.getchannel("A"))
    elif img.mode != "RGB":
        img = img.convert("RGB")
    if spec.rotate:
        img = img.rotate(spec.rotate, expand=True)

    bw, bh = spec.width + 2 * spec.bleed, spec.height + 2 * spec.bleed
    mm_per_px = min(img.width / bw, img.height / bh) ** -1  # cover: the tighter axis fills
    effective_dpi = 25.4 / mm_per_px
    crop_w, crop_h = bw / mm_per_px, bh / mm_per_px
    left, top = max(0.0, (img.width - crop_w) / 2), max(0.0, (img.height - crop_h) / 2)
    box = (left, top, min(img.width, left + crop_w), min(img.height, top + crop_h))
    dpi = min(spec.dpi, effective_dpi)
    out_size = (max(1, round(bw / 25.4 * dpi)), max(1, round(bh / 25.4 * dpi)))
    return img.resize(out_size, Image.Resampling.LANCZOS, box=box), effective_dpi


def to_page(x: float, y: float, dx: float, dy: float) -> pymupdf.Point:
    return pymupdf.Point((x + dx) * PT, (y + dy) * PT)


def rect_to_page(r: Rect, dx: float, dy: float) -> pymupdf.Rect:
    return pymupdf.Rect((r.x0 + dx) * PT, (r.y0 + dy) * PT, (r.x1 + dx) * PT, (r.y1 + dy) * PT)


def intersect(a: Rect, b: Rect) -> Rect | None:
    r = Rect(max(a.x0, b.x0), max(a.y0, b.y0), min(a.x1, b.x1), min(a.y1, b.y1))
    return r if r.x1 > r.x0 and r.y1 > r.y0 else None


def draw_image(page, spec: MapSpec, img: Image.Image, vis: Rect, dx: float, dy: float) -> None:
    b = spec.bleed
    sx = img.width / (spec.width + 2 * b)
    sy = img.height / (spec.height + 2 * b)
    left, top = round((vis.x0 + b) * sx), round((vis.y0 + b) * sy)
    right, bottom = round((vis.x1 + b) * sx), round((vis.y1 + b) * sy)
    tile = img.crop((left, top, right, bottom))
    buf = io.BytesIO()
    tile.save(buf, "JPEG", quality=JPEG_QUALITY)
    placed = Rect(left / sx - b, top / sy - b, right / sx - b, bottom / sy - b)
    page.insert_image(rect_to_page(placed, dx, dy), stream=buf.getvalue(), keep_proportion=False)


def draw_segments(page, segments, color, width: float, dx: float, dy: float) -> None:
    if not segments:
        return
    shape = page.new_shape()
    for a, b in segments:
        shape.draw_line(to_page(*a, dx, dy), to_page(*b, dx, dy))
    shape.finish(color=color, width=width * PT, lineCap=1, closePath=False)
    shape.commit()


def draw_map(page, spec: MapSpec, img: Image.Image, piece: Piece, dx: float, dy: float) -> None:
    vis = piece.visible
    draw_image(page, spec, img, vis, dx, dy)

    zones = spec.zones
    if zones:
        full = Rect(-spec.bleed, -spec.bleed, spec.width + spec.bleed, spec.height + spec.bleed)
        bars = [
            (zones.left, Rect(full.x0, full.y0, zones.bar_width, full.y1)),
            (zones.right, Rect(spec.width - zones.bar_width, full.y0, full.x1, full.y1)),
        ]
        for side, bar in bars:
            if side and side.bar and (r := intersect(bar, vis)):
                page.draw_rect(rect_to_page(r, dx, dy), color=None, fill=side.bar, width=0)

    grid = HexGrid.anchored(spec.hex_size) if spec.sized_by_hexes else HexGrid.centered(spec.width, spec.height, spec.hex_size)
    lines: GridLines = grid_lines(grid, spec.width, vis, zones.depth if zones else None)
    if not (zones and zones.left):
        lines.plain += lines.left
        lines.left = []
    if not (zones and zones.right):
        lines.plain += lines.right
        lines.right = []
    draw_segments(page, lines.all, spec.grid_under.color, spec.grid_under.width, dx, dy)
    draw_segments(page, lines.plain, spec.grid_over.color, spec.grid_over.width, dx, dy)
    if zones and zones.left:
        draw_segments(page, lines.left, zones.left.line, zones.width, dx, dy)
    if zones and zones.right:
        draw_segments(page, lines.right, zones.right.line, zones.width, dx, dy)


def draw_marks(page, spec: MapSpec, piece: Piece, dx: float, dy: float) -> None:
    vis, cut = piece.visible, piece.cut
    shape = page.new_shape()
    xs = [cut.x0] + ([cut.x1] if not piece.flap_right else [])
    ys = [cut.y0] + ([cut.y1] if not piece.flap_bottom else [])
    for x in xs:
        for y_from, sign in ((vis.y0, -1), (vis.y1, 1)):
            shape.draw_line(to_page(x, y_from + sign * MARK_GAP, dx, dy), to_page(x, y_from + sign * MARK_SPACE, dx, dy))
    for y in ys:
        for x_from, sign in ((vis.x0, -1), (vis.x1, 1)):
            shape.draw_line(to_page(x_from + sign * MARK_GAP, y, dx, dy), to_page(x_from + sign * MARK_SPACE, y, dx, dy))
    shape.finish(color=(0, 0, 0), width=MARK_WIDTH * PT, closePath=False)

    # Where the neighbouring piece's cut edge lands on this piece's flap.
    if piece.flap_right or piece.flap_bottom:
        if piece.flap_right:
            for y_from, sign in ((vis.y0, -1), (vis.y1, 1)):
                shape.draw_line(to_page(cut.x1, y_from + sign * MARK_GAP, dx, dy), to_page(cut.x1, y_from + sign * MARK_SPACE, dx, dy))
        if piece.flap_bottom:
            for x_from, sign in ((vis.x0, -1), (vis.x1, 1)):
                shape.draw_line(to_page(x_from + sign * MARK_GAP, cut.y1, dx, dy), to_page(x_from + sign * MARK_SPACE, cut.y1, dx, dy))
        shape.finish(color=(0.45, 0.45, 0.45), width=MARK_WIDTH * PT, dashes="[1.5 1] 0", closePath=False)
    shape.commit()

    small = 5.5
    if piece.flap_right:
        p = to_page((cut.x1 + vis.x1) / 2, vis.y1 + MARK_SPACE + 2.2, dx, dy)
        text = "OVERLAP"
        page.insert_text(pymupdf.Point(p.x - pymupdf.get_text_length(text, "helv", small) / 2, p.y), text, fontname="helv", fontsize=small, color=(0.45, 0.45, 0.45))
    if piece.flap_bottom:
        p = to_page(vis.x1 + MARK_SPACE + 1, (cut.y1 + vis.y1) / 2, dx, dy)
        page.insert_text(p, "OVERLAP", fontname="helv", fontsize=small, color=(0.45, 0.45, 0.45))


def text_at(page, x_mm: float, y_mm: float, text: str, size: float, bold: bool = False, align: str = "left") -> None:
    font = "hebo" if bold else "helv"
    width = pymupdf.get_text_length(text, font, size)
    x = x_mm * PT - {"left": 0, "center": width / 2, "right": width}[align]
    page.insert_text(pymupdf.Point(x, y_mm * PT), text, fontname=font, fontsize=size, color=(0, 0, 0))


def draw_furniture(page, sheet: Sheet, total: int) -> None:
    spec, piece = sheet.spec, sheet.piece
    pw, ph = page_size(spec, sheet.landscape)
    m = spec.margin
    text_at(page, m, m + 3, f"{spec.header} / {spec.paper.name} PRINT & CUT", 10, bold=True)
    text_at(page, pw - m, m + 3, f"SHEET {sheet.number} OF {total}", 8, align="right")
    text_at(page, m, m + 9, INSTRUCTIONS, 8)
    title = spec.title.upper()
    if piece.rows * piece.cols > 1:
        index = piece.row * piece.cols + piece.col + 1
        title += f" / PIECE {index} OF {piece.rows * piece.cols} (ROW {piece.row + 1}, COL {piece.col + 1})"
    text_at(page, pw - m, m + 9, title, 8, align="right")

    cx = pw / 2
    bar_y = ph - m - 8
    text_at(page, cx, bar_y - 4, f"SCALE CHECK: this line must measure {fmt(SCALE_BAR)} mm", 7.5, align="center")
    shape = page.new_shape()
    x0, x1 = cx - SCALE_BAR / 2, cx + SCALE_BAR / 2
    shape.draw_line(to_page(x0, bar_y, 0, 0), to_page(x1, bar_y, 0, 0))
    for x in (x0, x1):
        shape.draw_line(to_page(x, bar_y - 1.5, 0, 0), to_page(x, bar_y + 1.5, 0, 0))
    shape.finish(color=(0, 0, 0), width=MARK_WIDTH * PT, closePath=False)
    shape.commit()

    size = f"{fmt(spec.width)} x {fmt(spec.height)} mm"
    if piece.rows * piece.cols == 1:
        note = f"Finished size: {size}. Cut between corner marks; {fmt(spec.bleed)} mm bleed included."
    else:
        note = (
            f"Finished map: {size} in {piece.rows * piece.cols} pieces. Cut on the corner marks; "
            "lay each piece over its neighbour's overlap, edge on the dashed marks."
        )
    text_at(page, cx, bar_y + 5, note, 7.5, align="center")


def plan(specs: list[MapSpec]) -> list[Sheet]:
    sheets = []
    for spec in specs:
        landscape, pieces = choose_layout(spec)
        sheets.extend(Sheet(spec, p, landscape) for p in pieces)
    for n, sheet in enumerate(sheets, 1):
        sheet.number = n
    return sheets


def build(specs: list[MapSpec], output: Path) -> list[MapReport]:
    sheets = plan(specs)
    doc = pymupdf.open()
    reports: list[MapReport] = []
    images: dict[int, Image.Image] = {}
    for sheet in sheets:
        spec, piece = sheet.spec, sheet.piece
        if id(spec) not in images:
            img, eff = prepare_image(spec)
            images.clear()  # one map's artwork in memory at a time
            images[id(spec)] = img
            report = MapReport(spec, eff, piece.rows * piece.cols, piece.cols, piece.rows)
            if eff < spec.min_dpi:
                report.warnings.append(f"artwork is only {eff:.0f} DPI at print size (below {spec.min_dpi}); expect softness")
            reports.append(report)
        img = images[id(spec)]

        pw, ph = page_size(spec, sheet.landscape)
        page = doc.new_page(width=pw * PT, height=ph * PT)
        area = map_area(spec, sheet.landscape)
        vis = piece.visible
        dx = (area.x0 + area.x1) / 2 - (vis.x0 + vis.x1) / 2
        dy = (area.y0 + area.y1) / 2 - (vis.y0 + vis.y1) / 2
        draw_map(page, spec, img, piece, dx, dy)
        draw_marks(page, spec, piece, dx, dy)
        draw_furniture(page, sheet, len(sheets))

    first = specs[0]
    doc.set_metadata(
        {
            "title": f"{first.header.title()} - {first.paper.name} Print and Cut",
            "subject": f"{len(sheets)} sheets. Print at 100%.",
        }
    )
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output, garbage=3, deflate=True)
    return reports
