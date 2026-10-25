import pymupdf
import pytest
from PIL import Image

from greathelm_maps import build, load_config
from greathelm_maps.render import choose_layout, map_area, prepare_image, split_axis


@pytest.fixture
def art(tmp_path):
    path = tmp_path / "art.png"
    img = Image.new("RGBA", (400, 300), (0, 0, 0, 0))
    img.paste((200, 30, 30, 255), (0, 0, 200, 300))
    img.save(path)
    return path


def specs(tmp_path, art, extra=""):
    p = tmp_path / "maps.yaml"
    p.write_text(f"maps:\n  - {{image: {art.name}, {extra}}}\n")
    return load_config(p)


def test_split_axis():
    assert split_axis(100, 120, 2, 10) == [0, 100]
    cuts = split_axis(400, 140, 2, 10)
    assert cuts[0] == 0 and cuts[-1] == 400
    piece = cuts[1] - cuts[0]
    assert piece + 2 + 10 <= 140
    assert split_axis(100, 5, 2, 10) is None


def test_example_size_fits_one_landscape_a4(tmp_path, art):
    (spec,) = specs(tmp_path, art, "size: 185x131.25mm")
    landscape, pieces = choose_layout(spec)
    assert landscape and len(pieces) == 1


def test_large_map_tiles_cover_map_exactly(tmp_path, art):
    (spec,) = specs(tmp_path, art, "size: 600x400mm")
    landscape, pieces = choose_layout(spec)
    assert len(pieces) > 1
    area = map_area(spec, landscape)
    covered = sum(p.cut.width * p.cut.height for p in pieces)
    assert covered == pytest.approx(600 * 400)
    for p in pieces:
        assert p.visible.width <= area.width + 1e-9 and p.visible.height <= area.height + 1e-9
        assert p.visible.x0 >= -spec.bleed - 1e-9 and p.visible.x1 <= 600 + spec.bleed + 1e-9
        if p.flap_right:
            assert p.visible.x1 == pytest.approx(p.cut.x1 + spec.overlap)


def test_orientation_follows_map_shape(tmp_path, art):
    (spec,) = specs(tmp_path, art, "size: 100x150mm")
    landscape, pieces = choose_layout(spec)
    assert not landscape and len(pieces) == 1


def test_prepare_image_cover_crop_and_flatten(tmp_path, art):
    (spec,) = specs(tmp_path, art, "size: 96x96mm, bleed: 2mm, dpi: 100")
    img, eff = prepare_image(spec)
    # 300 px tall image covering 100 mm (96 + bleed): 76.2 DPI, not upsampled
    assert eff == pytest.approx(300 / (100 / 25.4))
    assert img.size == (300, 300)
    assert img.mode == "RGB"
    # left third (transparent) became white, centre crop keeps a red/white split
    assert img.getpixel((10, 150)) == (200, 30, 30)
    assert img.getpixel((290, 150)) == (255, 255, 255)


def test_rotate_is_anticlockwise(tmp_path, art):
    (spec,) = specs(tmp_path, art, "size: 75x100mm, bleed: 0, rotate: 90")
    img, _ = prepare_image(spec)
    # red left half of the source ends up at the bottom after a 90 degree anticlockwise turn
    assert img.getpixel((img.width // 2, img.height - 5)) == (200, 30, 30)
    assert img.getpixel((img.width // 2, 5)) == (255, 255, 255)


def test_build_reports_low_dpi_and_numbers_sheets(tmp_path, art):
    p = tmp_path / "maps.yaml"
    p.write_text(f"maps:\n  - {{image: {art.name}, size: 185x131.25mm}}\n  - {{image: {art.name}, size: 500x300mm}}\n")
    out = tmp_path / "out.pdf"
    reports = build(load_config(p), out)
    assert all(r.warnings for r in reports)
    doc = pymupdf.open(out)
    total = sum(r.pieces for r in reports)
    assert doc.page_count == total
    assert f"SHEET {total} OF {total}" in doc[-1].get_text()
    assert "PIECE" in doc[-1].get_text()
