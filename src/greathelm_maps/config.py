"""Load and validate the YAML build file.

All lengths are stored in millimetres. Lengths in the YAML may be bare numbers
(mm) or strings with a unit: ``15mm``, ``1.5cm``, ``0.5in``, ``12pt``.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

PAPER_SIZES = {
    "A5": (148.0, 210.0),
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A2": (420.0, 594.0),
    "A1": (594.0, 841.0),
    "LETTER": (215.9, 279.4),
    "LEGAL": (215.9, 355.6),
    "TABLOID": (279.4, 431.8),
}

UNITS_MM = {"mm": 1.0, "cm": 10.0, "in": 25.4, "pt": 25.4 / 72}

DEFAULTS = {
    "header": "GREATHELM",
    "paper": "A4",
    "margin": "10mm",
    "hex_size": "15mm",
    "bleed": "2mm",
    "dpi": 300,
    "min_dpi": 150,
    "overlap": "10mm",
    "rotate": 0,
    "grid": {
        "under": {"color": "#F4EEDB", "width": "0.725mm"},
        "over": {"color": "#363D32", "width": "0.35mm"},
    },
    "zones": {
        "depth": 3,
        "width": "0.425mm",
        "bar_width": "3.75mm",
        "left": {"line": "#B02F2D", "bar": "#C64D42"},
        "right": {"line": "#195FA9", "bar": "#347ABD"},
    },
}

# Keys allowed in a map entry on top of the defaults.
MAP_ONLY_KEYS = {"image", "title", "size", "hexes"}


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class LineStyle:
    color: tuple[float, float, float]
    width: float


@dataclass(frozen=True)
class ZoneSide:
    line: tuple[float, float, float]
    bar: tuple[float, float, float] | None


@dataclass(frozen=True)
class Zones:
    depth: int
    width: float
    bar_width: float
    left: ZoneSide | None
    right: ZoneSide | None


@dataclass(frozen=True)
class Paper:
    name: str
    width: float  # portrait width, mm
    height: float  # portrait height, mm


@dataclass(frozen=True)
class MapSpec:
    image: Path
    title: str
    width: float  # finished size, mm
    height: float
    sized_by_hexes: bool
    rotate: int
    header: str
    paper: Paper
    margin: float
    hex_size: float
    bleed: float
    dpi: int
    min_dpi: int
    overlap: float
    grid_under: LineStyle
    grid_over: LineStyle
    zones: Zones | None


def parse_length(value, field: str) -> float:
    if isinstance(value, bool):
        raise ConfigError(f"{field}: expected a length, got {value!r}")
    if isinstance(value, (int, float)):
        return float(value)
    m = re.fullmatch(r"\s*([0-9]*\.?[0-9]+)\s*(mm|cm|in|pt)?\s*", str(value))
    if not m:
        raise ConfigError(f"{field}: can't read length {value!r} (try '15mm')")
    return float(m.group(1)) * UNITS_MM[m.group(2) or "mm"]


def parse_pair(value, field: str, *, integer: bool = False) -> tuple:
    """Parse ``185x131.25mm``, ``14x9``, or a two-item list."""
    if isinstance(value, (list, tuple)):
        parts = list(value)
    else:
        text = str(value).strip()
        unit = ""
        m = re.search(r"(mm|cm|in|pt)\s*$", text)
        if m:
            unit = m.group(1)
            text = text[: m.start()]
        parts = [p.strip() for p in re.split(r"\s*[x×]\s*", text)]
        if unit:
            parts = [p if re.search(r"[a-z]$", p) else p + unit for p in parts]
    if len(parts) != 2:
        raise ConfigError(f"{field}: expected WIDTHxHEIGHT, got {value!r}")
    if integer:
        try:
            out = tuple(int(str(p)) for p in parts)
        except ValueError:
            raise ConfigError(f"{field}: expected whole numbers like 14x9, got {value!r}")
        if min(out) < 1:
            raise ConfigError(f"{field}: counts must be at least 1")
        return out
    out = tuple(parse_length(p, field) for p in parts)
    if min(out) <= 0:
        raise ConfigError(f"{field}: sizes must be positive")
    return out


def parse_color(value, field: str) -> tuple[float, float, float]:
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", str(value).strip())
    if not m:
        raise ConfigError(f"{field}: expected a hex colour like '#B02F2D', got {value!r}")
    h = m.group(1)
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def parse_paper(value) -> Paper:
    name = str(value).strip()
    if name.upper() in PAPER_SIZES:
        w, h = PAPER_SIZES[name.upper()]
        return Paper(name.upper() if name.upper().startswith("A") else name.title(), w, h)
    w, h = parse_pair(name, "paper")
    return Paper("CUSTOM", min(w, h), max(w, h))


def deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def check_keys(data: dict, allowed: set, where: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {', '.join(sorted(unknown))}")


def _line_style(data, field: str) -> LineStyle:
    check_keys(data, {"color", "width"}, field)
    return LineStyle(parse_color(data["color"], f"{field}.color"), parse_length(data["width"], f"{field}.width"))


def _zone_side(data, field: str) -> ZoneSide | None:
    if data is False or data is None:
        return None
    check_keys(data, {"line", "bar"}, field)
    bar = data.get("bar")
    return ZoneSide(
        parse_color(data["line"], f"{field}.line"),
        None if bar in (False, None) else parse_color(bar, f"{field}.bar"),
    )


def _zones(data, field: str) -> Zones | None:
    if data is False or data is None:
        return None
    merged = deep_merge(DEFAULTS["zones"], data) if data is not True else DEFAULTS["zones"]
    check_keys(merged, set(DEFAULTS["zones"]), field)
    depth = merged["depth"]
    if not isinstance(depth, int) or depth < 0:
        raise ConfigError(f"{field}.depth: expected a whole number of columns")
    return Zones(
        depth=depth,
        width=parse_length(merged["width"], f"{field}.width"),
        bar_width=parse_length(merged["bar_width"], f"{field}.bar_width"),
        left=_zone_side(merged["left"], f"{field}.left"),
        right=_zone_side(merged["right"], f"{field}.right"),
    )


def build_map_spec(entry: dict, defaults: dict, base_dir: Path, index: int) -> MapSpec:
    where = f"maps[{index}]"
    if not isinstance(entry, dict):
        raise ConfigError(f"{where}: expected a mapping")
    check_keys(entry, set(DEFAULTS) | MAP_ONLY_KEYS, where)
    # zones: false in an entry must replace, not merge
    data = deep_merge(defaults, {k: v for k, v in entry.items() if k != "zones"})
    if "zones" in entry:
        zones_value = entry["zones"]
        if isinstance(zones_value, dict) and isinstance(defaults.get("zones"), dict):
            zones_value = deep_merge(defaults["zones"], zones_value)
        data["zones"] = zones_value

    if "image" not in data:
        raise ConfigError(f"{where}: missing 'image'")
    image = (base_dir / str(data["image"])).resolve()
    if not image.is_file():
        raise ConfigError(f"{where}: image not found: {image}")
    title = str(data.get("title") or image.stem.replace("_", " ").replace("-", " ").title())

    hex_size = parse_length(data["hex_size"], f"{where}.hex_size")
    if ("size" in data) == ("hexes" in data):
        raise ConfigError(f"{where}: give exactly one of 'size' (mm) or 'hexes' (columns x rows)")
    if "size" in data:
        width, height = parse_pair(data["size"], f"{where}.size")
        sized_by_hexes = False
    else:
        from .geometry import size_for_hexes

        cols, rows = parse_pair(data["hexes"], f"{where}.hexes", integer=True)
        width, height = size_for_hexes(cols, rows, hex_size)
        sized_by_hexes = True

    rotate = data["rotate"]
    if rotate not in (0, 90, 180, 270):
        raise ConfigError(f"{where}.rotate: must be 0, 90, 180 or 270")

    grid = data["grid"]
    check_keys(grid, {"under", "over"}, f"{where}.grid")

    return MapSpec(
        image=image,
        title=title,
        width=width,
        height=height,
        sized_by_hexes=sized_by_hexes,
        rotate=rotate,
        header=str(data["header"]),
        paper=parse_paper(data["paper"]),
        margin=parse_length(data["margin"], f"{where}.margin"),
        hex_size=hex_size,
        bleed=parse_length(data["bleed"], f"{where}.bleed"),
        dpi=int(data["dpi"]),
        min_dpi=int(data["min_dpi"]),
        overlap=parse_length(data["overlap"], f"{where}.overlap"),
        grid_under=_line_style(grid["under"], f"{where}.grid.under"),
        grid_over=_line_style(grid["over"], f"{where}.grid.over"),
        zones=_zones(data["zones"], f"{where}.zones"),
    )


def load_config(path: Path) -> list[MapSpec]:
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: invalid YAML: {e}")
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: top level must be a mapping with 'maps'")
    check_keys(raw, {"defaults", "maps"}, str(path))
    user_defaults = raw.get("defaults") or {}
    check_keys(user_defaults, set(DEFAULTS), "defaults")
    defaults = deep_merge(DEFAULTS, {k: v for k, v in user_defaults.items() if k != "zones"})
    if "zones" in user_defaults:
        z = user_defaults["zones"]
        defaults["zones"] = deep_merge(DEFAULTS["zones"], z) if isinstance(z, dict) else z
    maps = raw.get("maps")
    if not maps:
        raise ConfigError(f"{path}: no maps listed")
    return [build_map_spec(entry, defaults, path.parent, i) for i, entry in enumerate(maps)]
