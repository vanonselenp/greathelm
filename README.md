# greathelm-maps

Turns map artwork into print-ready PDF sheets for the Greathelm wargame. The
hex grid, deployment zones, crop marks and scale check are drawn the same way
as in `docs/Greathelm-A4-print-and-cut.pdf`.

```sh
uv sync
uv run python scripts/extract_example_art.py      # sample artwork -> examples/art/
uv run greathelm-maps build examples/maps.yaml -o out/maps.pdf
```

## Config

```yaml
defaults:              # every key here can also be set per map
  header: GREATHELM
  paper: A4            # A5 A4 A3 A2 A1 Letter Legal Tabloid, or "300x400mm"
  margin: 10mm         # unprintable edge of the paper
  hex_size: 15mm       # flat-to-flat (distance between adjacent hex centres)
  bleed: 2mm
  dpi: 300             # artwork is downsampled to this, never upsampled
  min_dpi: 150         # warn below this
  overlap: 10mm        # glue flap between pieces of a tiled map
  rotate: 0            # 0/90/180/270, anticlockwise
  grid:
    under: {color: "#F4EEDB", width: 0.725mm}
    over:  {color: "#363D32", width: 0.35mm}
  zones:               # or `zones: false`
    depth: 3           # columns per side, counting the one cut by the edge
    width: 0.425mm
    bar_width: 3.75mm  # solid bar inside the trim line (also fills the bleed)
    left:  {line: "#B02F2D", bar: "#C64D42"}   # `left: false`, or `bar: false`
    right: {line: "#195FA9", bar: "#347ABD"}

maps:
  - image: art/my-map.png     # relative to this file
    title: 06 / River Crossing
    size: 185x131.25mm        # finished (trimmed) size...
  - image: art/other.jpg
    hexes: 14x9               # ...or 14 whole columns, 9 hexes tall
```

Units: bare numbers are mm; `mm`, `cm`, `in` and `pt` are accepted.

## How it lays out

- **Image fit:** the artwork is scaled to cover the map plus its bleed, and any
  overflow is cropped evenly from both sides. It is never stretched or
  rotated automatically.
- **Grid alignment with `size:`:** a column sits on the vertical centreline,
  raised a quarter hex. This matches the example sheets: the left and right
  edges cut the hexes the same way, and the top and bottom cut through the
  zig-zag.
- **Grid alignment with `hexes:`:** the first column is whole and its corners
  touch the left edge, the last column's corners touch the right edge, and
  every even column is whole top to bottom.
- **Orientation:** each map goes on the page orientation that needs the fewest
  sheets.
- **Tiling:** a map that doesn't fit on one sheet is split into equal pieces.
  Every piece except those in the last column and last row carries an overlap
  flap on its right and bottom edges. Cut each piece on its corner marks and
  lay it over its neighbour's flap, lining the edge up with the dashed marks.
- **Sheet numbering:** sheets are numbered across the whole PDF.

## Tests

```sh
uv run pytest
```

`tests/test_example_match.py` rebuilds the quickstart sheet from the example
PDF's own artwork. It checks that every hex corner, zone edge, edge bar and
crop mark lands within 0.01 mm of the original.
