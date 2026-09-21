"""His fills as tiles: every layer of a symbol in one repeating tile (doc 97).

SVG fills a shape with one pattern, and a pattern repeats with one period; his
layers each have their own — a texture 80 points high, splotches every 30 by
98, tufts every 72 by 48. So the tile is a whole number of his textures across
and down, and every strewn layer gets a whole number of cells in it: steps
moved by a few per cent, which a random scatter does not show. A mark that
reaches over the tile's edge is drawn again on the far side, or the edge would
cut it off in a straight line.

Sizes are his, in points at print scale, converted to metres at one reference
scale. Placement is his random grid — one mark per cell, displaced within it —
seeded with his seed, so a run places every mark where the last one did.
"""
from __future__ import annotations

import hashlib
import math
import random

from scripts.draft_sketch import png
from scripts.draft_sketch.cim import Colour, Layer
from scripts.draft_sketch.emit import Lines, Mark, Paper, Pattern, Piece, Ring, Sheet, number

#: The plan's scale at which his marks are the size he drew them.
REFERENCE_SCALE = 250
#: One of his points, in metres on the ground.
POINT_M = 0.0254 / 72 * REFERENCE_SCALE
#: A tile at least this big, in points, so that the scatter does not read as a grid.
TILE_PT = 200.0
#: Without a texture to fit, a tile is this many of its widest step.
TILE_STEPS = 6
#: A strewn layer repeats on a sheet of at least this many of its marks, not
#: across the whole tile: a dense scatter — grains of sand, splotches on a
#: crown, ripples — does not show where a sheet of a dozen starts again, and
#: hundreds of marks per tile were most of what a browser had to style.
SHEET_MARKS = 12
#: At most this bright, an image is ink: drawn as it is when he tints it black.
DARK = 0.2
BLACK = "#000000"
Tile = tuple[float, float]


class Images:
    """His images, each once, keyed by content — and only those the theme draws."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self._seen: dict[str, png.Image] = {}

    def _image(self, data: bytes) -> tuple[str, png.Image]:
        key = "ds-" + hashlib.sha256(data).hexdigest()[:8]
        if key not in self._seen:
            self._seen[key] = png.decode(data)
        return key, self._seen[key]

    def ship(self, data: bytes) -> str:
        """An image the theme draws: kept, and named by its key."""
        key, _ = self._image(data)
        self.files[key] = data
        return key

    def aspect(self, data: bytes) -> float:
        _, image = self._image(data)
        return image.width / image.height

    def coverage(self, data: bytes) -> float:
        _, image = self._image(data)
        return png.coverage(image)

    def tint(self, data: bytes, colour: Colour) -> str | None:
        """How the image is drawn in his tint. A tint multiplies — his own style
        sheet shows it: a white wash takes the tint's colour, and black ink
        stays black whatever it is tinted (his trees' "white" strokes are
        black). So ink is drawn as it is (None), a wash as his colour through
        its alpha, and anything in between is refused: multiplying a grey image
        is more than a mask can do."""
        _, image = self._image(data)
        light = png.brightness(image)
        if light <= DARK:
            return None
        if png.is_wash(image):
            return colour.hex
        raise ValueError(f"a {colour.hex} tint on an image neither white nor ink ({light:.2f})")

    def ink(self, data: bytes, colour: Colour) -> str:
        """The one colour the image comes out as in this tint."""
        return BLACK if self.tint(data, colour) is None else colour.hex


def _paper_size(layer: Layer, images: Images) -> Tile:
    if layer.rotation % 360:
        raise ValueError("a turned texture")
    return layer.size_pt * images.aspect(layer.image), layer.size_pt


def tile_of(layers: list[Layer], images: Images) -> Tile:
    """The tile, in points: whole textures across and down, or whole steps."""
    papers = {_paper_size(layer, images) for layer in layers if layer.kind == "paper"}
    if len(papers) > 1:
        raise ValueError("textures of two sizes in one symbol")
    if papers:
        (width, height), = papers
        return width * math.ceil(TILE_PT / width), height * math.ceil(TILE_PT / height)
    strewn = [layer for layer in layers if layer.kind in ("scatter", "grains")]
    steps = [step for layer in strewn for step in layer.step_pt]
    side = TILE_STEPS * max(steps) if steps else TILE_PT
    return side, side


def _grid(layer: Layer, tile: Tile) -> tuple[int, int]:
    """His step, fitted to a whole number of cells across and down the tile."""
    return max(1, round(tile[0] / layer.step_pt[0])), max(1, round(tile[1] / layer.step_pt[1]))


def _strewn(layer: Layer, tile: Tile, grid: tuple[int, int] | None = None,
            ) -> list[tuple[float, float]]:
    """Where his random grid puts its marks: one per cell, displaced within it."""
    cols, rows = _grid(layer, tile) if grid is None else grid
    cell_w, cell_h = tile[0] / cols, tile[1] / rows
    rng = random.Random(layer.seed)
    spots = []
    for row in range(rows):
        for col in range(cols):
            dx, dy = rng.random() - 0.5, rng.random() - 0.5
            spots.append(((col + 0.5 + dx * layer.randomness) * cell_w,
                          (row + 0.5 + dy * layer.randomness) * cell_h))
    return spots


def _wrapped(x: float, y: float, reach: float, tile: Tile) -> list[tuple[float, float]]:
    """A spot, and a copy across every edge that a mark `reach` around it crosses."""
    width, height = tile
    return [(x + dx, y + dy) for dy in (-height, 0.0, height) for dx in (-width, 0.0, width)
            if -reach < x + dx < width + reach and -reach < y + dy < height + reach]


def _divisors(n: int) -> list[int]:
    return [d for d in range(1, n + 1) if n % d == 0]


def _sheet(layer: Layer, tile: Tile) -> tuple[Tile, list[tuple[float, float]]]:
    """The layer's sheet — the fewest whole cells of its grid holding at least
    SHEET_MARKS marks, a whole fraction of the tile — and its marks' spots."""
    cols, rows = _grid(layer, tile)
    across, down = min(
        ((c, r) for c in _divisors(cols) for r in _divisors(rows)
         if c * r >= min(SHEET_MARKS, cols * rows)),
        key=lambda grid: (grid[0] * grid[1], abs(grid[0] - grid[1])))
    sheet = (tile[0] / cols * across, tile[1] / rows * down)
    return sheet, _strewn(layer, sheet, (across, down))


def _scatter(layer: Layer, tile: Tile, images: Images) -> list[Piece]:
    height = layer.size_pt
    width = height * images.aspect(layer.image)
    tint, key = images.tint(layer.image, layer.colour), images.ship(layer.image)
    reach = math.hypot(width, height) / 2
    sheet, spots = _sheet(layer, tile)
    marks = tuple(
        Mark(key, x * POINT_M, y * POINT_M, width * POINT_M, height * POINT_M,
             # CIM turns counter-clockwise; SVG, with y down, clockwise.
             -layer.rotation, tint, layer.colour.opacity)
        for spot in spots for x, y in _wrapped(*spot, reach, sheet)
    )
    return [Sheet(sheet[0] * POINT_M, sheet[1] * POINT_M, marks)]


def _grains(layer: Layer, tile: Tile) -> list[Piece]:
    radius = layer.size_pt / 2
    reach = radius + layer.width_pt / 2
    sheet, spots = _sheet(layer, tile)
    rings = tuple(
        Ring(x * POINT_M, y * POINT_M, radius * POINT_M, layer.width_pt * POINT_M,
             layer.colour.hex, layer.colour.opacity)
        for spot in spots for x, y in _wrapped(*spot, reach, sheet)
    )
    return [Sheet(sheet[0] * POINT_M, sheet[1] * POINT_M, rings)]


def _hatch(layer: Layer, tile: Tile, images: Images) -> list[Piece]:
    if layer.rotation % 90:
        raise ValueError("a hatch at an angle other than a right one")
    level = layer.rotation % 180 == 0
    across, along = (tile[1], tile[0]) if level else (tile[0], tile[1])
    count = max(1, round(across / layer.separation_pt))
    gap = across / count
    # His strip lays down this share of ink; drawn solid, it is that much narrower.
    width = layer.width_pt * (images.coverage(layer.image) if layer.image else 1.0)
    at: list[float] = []
    for k in range(count):
        line = (layer.shift_pt + k * gap) % across
        at += [line] + ([line + across] if line < width / 2 else [])
        at += [line - across] if line > across - width / 2 else []
    run = number(along * POINT_M)
    d = " ".join(f"M0 {number(a * POINT_M)}H{run}" if level else f"M{number(a * POINT_M)} 0V{run}"
                 for a in sorted(at))
    return [Lines(d, width * POINT_M, layer.colour.hex, layer.colour.opacity)]


def _paper(layer: Layer, images: Images) -> list[Piece]:
    width, height = _paper_size(layer, images)
    tint, key = images.tint(layer.image, layer.colour), images.ship(layer.image)
    return [Paper(key, width * POINT_M, height * POINT_M, tint, layer.colour.opacity)]


def _base(layers: list[Layer]) -> Colour | None:
    """The colour under everything: his plain fill, or the inside of a ramp
    that runs in from the edge — the rim is the part SVG cannot draw."""
    plain = [layer for layer in layers if layer.kind == "fill" and layer.move_pt == (0.0, 0.0)]
    if len(plain) > 1:
        raise ValueError("two plain fills in one symbol")
    if plain:
        return plain[0].colour
    inward = [layer.ramp for layer in layers
              if layer.kind == "gradient" and layer.method == "Buffered" and layer.ramp is not None]
    return inward[0][1] if inward and inward[0] is not None else None


def paper_of(pattern_id: str, layers: list[Layer], images: Images) -> Pattern | None:
    """His paper on its own, without the wash it carries — the sheet a plan is
    drawn on (doc 99). The tile is the texture's own size, so it repeats the way
    it does under every wash he paints, and the tint is the one his file gives
    it: nothing here is a colour of ours."""
    papers = [layer for layer in layers if layer.kind == "paper"]
    if not papers:
        return None
    width, height = _paper_size(papers[0], images)
    return Pattern(pattern_id, width * POINT_M, height * POINT_M, None, 1.0,
                   tuple(_paper(papers[0], images)))


def pattern_of(pattern_id: str, layers: list[Layer], images: Images) -> Pattern | None:
    """The symbol's fill as one tile, or None if it fills nothing."""
    base = _base(layers)
    tile = tile_of(layers, images)
    pieces: list[Piece] = []
    for layer in reversed(layers):  # his list is top first; a tile paints bottom first
        if layer.kind == "paper":
            pieces += _paper(layer, images)
        elif layer.kind == "scatter":
            pieces += _scatter(layer, tile, images)
        elif layer.kind == "grains":
            pieces += _grains(layer, tile)
        elif layer.kind == "hatch":
            pieces += _hatch(layer, tile, images)
    if base is None and not pieces:
        return None
    return Pattern(pattern_id, tile[0] * POINT_M, tile[1] * POINT_M,
                   None if base is None else base.hex, 1.0 if base is None else base.opacity,
                   tuple(pieces))


__all__ = ["POINT_M", "REFERENCE_SCALE", "Images", "paper_of", "pattern_of", "tile_of"]
