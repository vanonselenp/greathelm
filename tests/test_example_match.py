"""Rebuild the example's quickstart sheet and compare it to the original."""

import math

import pymupdf
import pytest

from greathelm_maps import build, load_config

MM = 72 / 25.4
TOL = 0.01  # mm

FINISHED = (56.0, 39.375, 241.0, 170.625)  # page mm, from the example's crop marks
BLEED = 2.0


def mm(p):
    return (p.x / MM, p.y / MM)


def close(a, b, tol=TOL):
    return math.dist(a, b) <= tol


@pytest.fixture(scope="module")
def pages(tmp_path_factory, example_pdf, quickstart_art):
    d = tmp_path_factory.mktemp("build")
    cfg = d / "maps.yaml"
    cfg.write_text(
        f"maps:\n  - {{image: {quickstart_art}, title: 05 / Quickstart Map, size: 185x131.25mm, rotate: 90}}\n"
    )
    out = d / "out.pdf"
    build(load_config(cfg), out)
    ours = pymupdf.open(out)
    theirs = pymupdf.open(example_pdf)
    yield ours[0], theirs[-1]
    ours.close()
    theirs.close()


def example_hexes(page):
    """{line colour: [6 corner points]} for the example's hex outlines."""
    hexes = {}
    for d in page.get_drawings():
        if len(d["items"]) == 6 and all(i[0] == "l" for i in d["items"]):
            hexes.setdefault(tuple(round(c, 3) for c in d["color"]), []).append([mm(i[1]) for i in d["items"]])
    return hexes


def our_segments(page):
    """{line colour: [(a, b)]} for our grid segments."""
    segs = {}
    for d in page.get_drawings():
        if d.get("color") and d["width"] < 3 and d["items"] and all(i[0] == "l" for i in d["items"]):
            for _, a, b in d["items"]:
                segs.setdefault(tuple(round(c, 3) for c in d["color"]), []).append((mm(a), mm(b)))
    return segs


def on_clip_edge(p):
    x0, y0, x1, y1 = (FINISHED[0] - BLEED, FINISHED[1] - BLEED, FINISHED[2] + BLEED, FINISHED[3] + BLEED)
    return min(abs(p[0] - x0), abs(p[0] - x1), abs(p[1] - y0), abs(p[1] - y1)) < 1e-3


def test_page_is_a4_landscape(pages):
    ours, theirs = pages
    assert ours.rect.width == pytest.approx(theirs.rect.width, abs=0.01)
    assert ours.rect.height == pytest.approx(theirs.rect.height, abs=0.01)


def test_hex_corners_match(pages):
    ours, theirs = pages
    corners = {c for hexes in example_hexes(theirs).values() for h in hexes for c in h}
    cream = (0.957, 0.933, 0.859)
    ends = [p for seg in our_segments(ours)[cream] for p in seg]
    assert ends

    interior = [p for p in ends if not on_clip_edge(p)]
    for p in interior:
        assert any(close(p, c) for c in corners), f"our corner {p} is not in the example"

    x0, y0, x1, y1 = FINISHED[0] - BLEED, FINISHED[1] - BLEED, FINISHED[2] + BLEED, FINISHED[3] + BLEED
    inside = [c for c in corners if x0 + TOL < c[0] < x1 - TOL and y0 + TOL < c[1] < y1 - TOL]
    assert len(inside) > 200
    for c in inside:
        assert any(close(p, c) for p in interior), f"example corner {c} missing from ours"


def point_on_hex_edge(p, hexes):
    for h in hexes:
        for k in range(6):
            a, b = h[k], h[(k + 1) % 6]
            ab = math.dist(a, b)
            if abs(math.dist(a, p) + math.dist(p, b) - ab) < TOL:
                return True
    return False


@pytest.mark.parametrize("ours_colour,theirs_colour", [((0.69, 0.184, 0.176), (0.69, 0.184, 0.176)), ((0.098, 0.373, 0.663), (0.098, 0.373, 0.663))])
def test_zone_edges_belong_to_zone_hexes(pages, ours_colour, theirs_colour):
    ours, theirs = pages
    zone_hexes = example_hexes(theirs)[theirs_colour]
    segs = our_segments(ours)[ours_colour]
    assert segs
    for a, b in segs:
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        assert point_on_hex_edge(mid, zone_hexes)


def filled_rects(page):
    out = {}
    for d in page.get_drawings():
        if d.get("fill") and len(d["items"]) == 1 and d["items"][0][0] == "re":
            r = d["items"][0][1]
            out[tuple(round(c, 3) for c in d["fill"])] = (r.x0 / MM, r.y0 / MM, r.x1 / MM, r.y1 / MM)
    return out


def test_edge_bars_match(pages):
    ours, theirs = pages
    clip = (FINISHED[0] - BLEED, FINISHED[1] - BLEED, FINISHED[2] + BLEED, FINISHED[3] + BLEED)
    ours_bars, theirs_bars = filled_rects(ours), filled_rects(theirs)
    for colour in [(0.776, 0.302, 0.259), (0.204, 0.478, 0.741)]:
        t = theirs_bars[colour]
        t = (max(t[0], clip[0]), max(t[1], clip[1]), min(t[2], clip[2]), min(t[3], clip[3]))
        assert ours_bars[colour] == pytest.approx(t, abs=TOL)


def test_artwork_covers_bleed(pages):
    ours, _ = pages
    rect = ours.get_image_rects(ours.get_images()[0][0])[0]
    got = (rect.x0 / MM, rect.y0 / MM, rect.x1 / MM, rect.y1 / MM)
    want = (FINISHED[0] - BLEED, FINISHED[1] - BLEED, FINISHED[2] + BLEED, FINISHED[3] + BLEED)
    assert got == pytest.approx(want, abs=0.2)  # within one artwork pixel


def black_lines(page):
    lines = []
    for d in page.get_drawings():
        if d.get("color") == (0.0, 0.0, 0.0):
            for item in d["items"]:
                if item[0] == "l":
                    lines.append(tuple(sorted([mm(item[1]), mm(item[2])])))
    return lines


def test_crop_marks_match(pages):
    ours, theirs = pages
    # Crop marks are the short black lines beside the map; the rest is the scale bar.
    crop = lambda lines: [l for l in lines if l[0][1] < 185]
    ours_marks, theirs_marks = crop(black_lines(ours)), crop(black_lines(theirs))
    assert len(ours_marks) == len(theirs_marks) == 8
    for t in theirs_marks:
        assert any(close(o[0], t[0], TOL) and close(o[1], t[1], TOL) for o in ours_marks), f"missing mark {t}"


def test_scale_bar_is_50mm(pages):
    ours, _ = pages
    bars = [l for l in black_lines(ours) if l[0][1] > 185 and abs(l[0][1] - l[1][1]) < 1e-6]
    assert len(bars) == 1
    assert math.dist(*bars[0]) == pytest.approx(50.0, abs=TOL)
