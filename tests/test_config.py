import pytest
from PIL import Image

from greathelm_maps.config import ConfigError, load_config, parse_length, parse_pair


@pytest.fixture
def art(tmp_path):
    path = tmp_path / "art.png"
    Image.new("RGB", (200, 100), (10, 120, 40)).save(path)
    return path


def write(tmp_path, text):
    p = tmp_path / "maps.yaml"
    p.write_text(text)
    return p


@pytest.mark.parametrize("value,mm", [(15, 15), ("15mm", 15), ("1.5cm", 15), ("1in", 25.4), ("72pt", 25.4), (" 2 mm ", 2)])
def test_parse_length(value, mm):
    assert parse_length(value, "x") == pytest.approx(mm)


@pytest.mark.parametrize("value", ["abc", "15km", True, "-3mm"])
def test_parse_length_rejects(value):
    with pytest.raises(ConfigError):
        parse_length(value, "x")


def test_parse_pair():
    assert parse_pair("185x131.25mm", "s") == (185, 131.25)
    assert parse_pair("18.5cm x 10cm", "s") == pytest.approx((185, 100))
    assert parse_pair([100, "5cm"], "s") == (100, 50)
    assert parse_pair("14x9", "h", integer=True) == (14, 9)
    with pytest.raises(ConfigError):
        parse_pair("14x0", "h", integer=True)


def test_defaults_and_overrides(tmp_path, art):
    cfg = write(
        tmp_path,
        f"""
defaults:
  paper: A3
  hex_size: 20mm
  zones: {{depth: 2}}
maps:
  - {{image: {art.name}, size: 185x131.25mm}}
  - image: {art.name}
    title: Custom
    hexes: 10x6
    paper: letter
    zones: {{left: {{line: "#000000", bar: false}}}}
  - {{image: {art.name}, size: 100x100, zones: false}}
""",
    )
    a, b, c = load_config(cfg)
    assert a.paper.name == "A3" and a.hex_size == 20 and a.zones.depth == 2
    assert a.title == "Art"
    assert b.sized_by_hexes and b.paper.name == "Letter"
    assert b.zones.depth == 2 and b.zones.left.line == (0, 0, 0) and b.zones.left.bar is None
    assert b.zones.right is not None
    assert c.zones is None


@pytest.mark.parametrize(
    "entry,message",
    [
        ("{image: missing.png, size: 10x10}", "image not found"),
        ("{image: art.png}", "exactly one of"),
        ("{image: art.png, size: 10x10, hexes: 3x3}", "exactly one of"),
        ("{image: art.png, size: 10x10, rotate: 45}", "rotate"),
        ("{image: art.png, size: 10x10, colour: red}", "unknown key"),
        ("{image: art.png, size: 10x10, grid: {over: {color: nope, width: 1}}}", "hex colour"),
    ],
)
def test_config_errors(tmp_path, art, entry, message):
    cfg = write(tmp_path, f"maps:\n  - {entry}\n")
    with pytest.raises(ConfigError, match=message):
        load_config(cfg)
