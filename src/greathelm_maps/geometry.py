"""Flat-topped hex grid maths, in map millimetres.

Map coordinates put (0, 0) at the top-left corner of the finished (trimmed)
map, with y pointing down. Columns are indexed by ``i`` and hexes within a
column by ``j``; odd columns sit half a hex lower than even ones.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

SQRT3 = math.sqrt(3)

Point = tuple[float, float]
Segment = tuple[Point, Point]


@dataclass(frozen=True)
class Rect:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def expand(self, d: float) -> Rect:
        return Rect(self.x0 - d, self.y0 - d, self.x1 + d, self.y1 + d)


def size_for_hexes(cols: int, rows: int, flat: float) -> tuple[float, float]:
    """Finished size holding ``cols`` whole columns of ``rows`` hexes.

    Width runs corner to corner across the outer columns; height is ``rows``
    hexes, so even columns are whole and odd columns are halved top and bottom.
    """
    r = flat / SQRT3
    return r * (1.5 * cols + 0.5), rows * flat


@dataclass(frozen=True)
class HexGrid:
    flat: float  # flat-to-flat size
    origin_x: float  # centre x of column 0
    origin_y: float  # centre y of hex 0 in column 0

    @classmethod
    def centered(cls, width: float, height: float, flat: float) -> HexGrid:
        """Grid phased like the Greathelm print-and-cut maps.

        A column sits on the vertical centreline, raised a quarter hex, so the
        grid is symmetric left/right and the zig-zag is centred vertically.
        """
        return cls(flat, width / 2, height / 2 - flat / 4)

    @classmethod
    def anchored(cls, flat: float) -> HexGrid:
        """Column 0 whole, touching the top-left corner (used with ``hexes:``)."""
        return cls(flat, flat / SQRT3, flat / 2)

    @property
    def radius(self) -> float:
        return self.flat / SQRT3

    @property
    def pitch_x(self) -> float:
        return 1.5 * self.radius

    def center(self, i: int, j: int) -> Point:
        y = self.origin_y + j * self.flat + (self.flat / 2 if i % 2 else 0.0)
        return self.origin_x + i * self.pitch_x, y

    def corners(self, i: int, j: int) -> list[Point]:
        cx, cy = self.center(i, j)
        r = self.radius
        return [(cx + r * math.cos(math.radians(60 * k)), cy + r * math.sin(math.radians(60 * k))) for k in range(6)]

    def columns_touching(self, x0: float, x1: float) -> range:
        """Column indices whose hexes overlap the open interval (x0, x1)."""
        r = self.radius
        first = math.floor((x0 + r - self.origin_x) / self.pitch_x)
        last = math.ceil((x1 - r - self.origin_x) / self.pitch_x)
        cols = [i for i in range(first, last + 1) if self.origin_x + i * self.pitch_x - r < x1 and self.origin_x + i * self.pitch_x + r > x0]
        return range(cols[0], cols[-1] + 1) if cols else range(0)

    def cells_touching(self, rect: Rect):
        h = self.flat / 2
        for i in self.columns_touching(rect.x0, rect.x1):
            shift = h if i % 2 else 0.0
            first = math.floor((rect.y0 - self.origin_y - shift - h) / self.flat)
            last = math.ceil((rect.y1 - self.origin_y - shift + h) / self.flat)
            for j in range(first, last + 1):
                cy = self.center(i, j)[1]
                if cy - h < rect.y1 and cy + h > rect.y0:
                    yield i, j


def clip_segment(seg: Segment, rect: Rect) -> Segment | None:
    """Liang-Barsky clip of a segment to a rectangle."""
    (x0, y0), (x1, y1) = seg
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - rect.x0), (dx, rect.x1 - x0), (-dy, y0 - rect.y0), (dy, rect.y1 - y0)):
        if p == 0:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    if t1 - t0 < 1e-9:
        return None
    return (x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy)


def _key(p: Point) -> tuple[int, int]:
    return round(p[0] * 1000), round(p[1] * 1000)


@dataclass
class GridLines:
    plain: list[Segment]
    left: list[Segment]
    right: list[Segment]

    @property
    def all(self) -> list[Segment]:
        return self.plain + self.left + self.right


def zone_columns(grid: HexGrid, width: float, depth: int) -> tuple[int | None, int | None]:
    """Last column of the left zone and first column of the right zone.

    ``depth`` counts columns that show on the finished map, so a column cut by
    the edge counts. Columns entirely off the map beyond them are included.
    """
    visible = grid.columns_touching(0.0, width)
    if depth <= 0 or not visible:
        return None, None
    return visible.start + depth - 1, visible.stop - depth


def grid_lines(grid: HexGrid, width: float, clip: Rect, depth: int | None) -> GridLines:
    """Unique hex edges clipped to ``clip``, split by deployment zone.

    An edge belongs to a zone if either hex it borders is in that zone.
    """
    left_end, right_start = zone_columns(grid, width, depth) if depth else (None, None)
    edges: dict[tuple, tuple[Segment, str]] = {}
    rank = {"plain": 0, "right": 1, "left": 2}
    for i, j in grid.cells_touching(clip):
        if left_end is not None and i <= left_end:
            kind = "left"
        elif right_start is not None and i >= right_start:
            kind = "right"
        else:
            kind = "plain"
        pts = grid.corners(i, j)
        for k in range(6):
            a, b = pts[k], pts[(k + 1) % 6]
            key = tuple(sorted((_key(a), _key(b))))
            if key not in edges or rank[kind] > rank[edges[key][1]]:
                edges[key] = ((a, b), kind)
    out = GridLines([], [], [])
    for seg, kind in edges.values():
        clipped = clip_segment(seg, clip)
        if clipped:
            getattr(out, kind).append(clipped)
    return out
