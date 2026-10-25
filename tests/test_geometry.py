import math

import pytest

from greathelm_maps.geometry import HexGrid, Rect, clip_segment, grid_lines, size_for_hexes, zone_columns


def test_centered_grid_matches_example_phase():
    g = HexGrid.centered(185, 131.25, 15)
    assert g.center(0, 0) == pytest.approx((92.5, 61.875))
    assert g.center(1, 0)[1] - g.center(0, 0)[1] == pytest.approx(7.5)
    assert g.pitch_x == pytest.approx(15 * math.sqrt(3) / 2)


def test_corners_are_flat_topped_and_size_is_flat_to_flat():
    g = HexGrid(15, 0, 0)
    ys = sorted(round(y, 9) for _, y in g.corners(0, 0))
    assert ys[0] == pytest.approx(-7.5) and ys[-1] == pytest.approx(7.5)
    xs = [x for x, _ in g.corners(0, 0)]
    assert max(xs) - min(xs) == pytest.approx(2 * 15 / math.sqrt(3))


def test_size_for_hexes_fits_whole_columns():
    w, h = size_for_hexes(14, 9, 15)
    g = HexGrid.anchored(15)
    assert h == 135
    assert g.center(0, 0)[0] - g.radius == pytest.approx(0)
    assert g.center(13, 0)[0] + g.radius == pytest.approx(w)
    assert g.center(0, 0)[1] - 7.5 == pytest.approx(0)
    assert g.center(0, 8)[1] + 7.5 == pytest.approx(h)


def test_clip_segment():
    r = Rect(0, 0, 10, 10)
    assert clip_segment(((-5, 5), (15, 5)), r) == ((0, 5), (10, 5))
    assert clip_segment(((2, 2), (3, 3)), r) == ((2, 2), (3, 3))
    assert clip_segment(((-5, -5), (-1, 20)), r) is None
    assert clip_segment(((0, -5), (0, 15)), r) == ((0, 0), (0, 10))


def test_zone_depth_counts_columns_cut_by_the_edge():
    g = HexGrid.centered(185, 131.25, 15)
    visible = g.columns_touching(0, 185)
    assert len(visible) == 15
    left_end, right_start = zone_columns(g, 185, 3)
    assert left_end == visible.start + 2
    assert right_start == visible.stop - 3


def test_grid_lines_are_unique_and_clipped():
    g = HexGrid.centered(185, 131.25, 15)
    clip = Rect(-2, -2, 187, 133.25)
    lines = grid_lines(g, 185, clip, 3)
    segs = lines.all
    keys = {tuple(sorted((tuple(round(c, 6) for c in a), tuple(round(c, 6) for c in b)))) for a, b in segs}
    assert len(keys) == len(segs)
    for a, b in segs:
        for x, y in (a, b):
            assert clip.x0 - 1e-9 <= x <= clip.x1 + 1e-9 and clip.y0 - 1e-9 <= y <= clip.y1 + 1e-9
    assert lines.left and lines.right and lines.plain
    assert max(x for s in lines.left for x, _ in s) < 185 / 2
    assert min(x for s in lines.right for x, _ in s) > 185 / 2


def test_no_zones_means_all_plain():
    g = HexGrid.centered(100, 100, 15)
    lines = grid_lines(g, 100, Rect(0, 0, 100, 100), None)
    assert not lines.left and not lines.right and lines.plain
