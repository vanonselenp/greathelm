"""Command line entry point: ``greathelm-maps build maps.yaml -o maps.pdf``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .geometry import SQRT3
from .render import build, fmt


def describe(spec) -> str:
    cols = (spec.width / (spec.hex_size / SQRT3) - 0.5) / 1.5
    rows = spec.height / spec.hex_size
    return f"{fmt(spec.width)} x {fmt(spec.height)} mm (~{cols:.1f} columns x {rows:.2f} hexes of {fmt(spec.hex_size)} mm)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="greathelm-maps", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="build a print-ready PDF from a YAML map list")
    b.add_argument("config", type=Path, help="YAML file listing the maps")
    b.add_argument("-o", "--output", type=Path, default=Path("maps.pdf"), help="PDF to write (default: maps.pdf)")
    args = parser.parse_args(argv)

    try:
        specs = load_config(args.config)
        reports = build(specs, args.output)
    except (ConfigError, ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    sheets = 0
    for r in reports:
        pieces = f"{r.pieces} sheets ({r.cols} x {r.rows})" if r.pieces > 1 else "1 sheet"
        print(f"{r.spec.title}: {describe(r.spec)}, {pieces}, artwork {r.effective_dpi:.0f} DPI", flush=True)
        for w in r.warnings:
            print(f"  warning: {w}", file=sys.stderr)
        sheets += r.pieces
    print(f"wrote {args.output} ({sheets} sheets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
