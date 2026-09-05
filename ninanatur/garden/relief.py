"""Turning heights into something an eye can read.

A grid of metres tells a reader nothing — 252.8 to 278.6 is a column of numbers.
The same grid lit from an angle is a landscape at a glance, which is why every
map in the world does this and why it is worth the twenty lines.

Computed here rather than in the browser. The server has the heights already;
sending 40,000 metre values so a browser can do the same arithmetic would be
five times the payload for the same picture.
"""
from __future__ import annotations

import math

from ninanatur.geo.terrain import TerrainWindow

#: Where the imaginary lamp stands. North-west at 45° is the cartographic
#: convention, and it is a convention rather than a fact: lighting relief from
#: the south-east makes valleys read as ridges to most people. Worth keeping
#: even though the sun never stands in the north-west in Germany.
LIGHT_AZIMUTH_DEG = 315.0
LIGHT_ALTITUDE_DEG = 45.0

#: How much the relief is exaggerated before it is lit. A garden's ground falls
#: a couple of metres across a couple of hundred, which is invisible at true
#: scale — the same reason every relief map in an atlas is exaggerated too.
EXAGGERATION = 3.0


def relief_of(window: TerrainWindow) -> list[float]:
    """How each cell stands to the lamp: **0.5 is level**, 1 faces it, 0 away.

    Relative to level rather than absolute, and that is the contract rather than
    a detail. Lit absolutely, flat ground comes out at 0.854 — the cosine of the
    lamp's own altitude — and a drawing that treats 0.5 as its neutral would then
    wash the entire plan in a uniform tint. Anchoring level at 0.5 here means the
    drawing can say "how far from level, and which way" with one subtraction and
    draw nothing at all where the answer is nothing.

    Unsurveyed ground comes back as 0.5, which is now the same thing as level:
    a gap in a picture is something somebody has to explain, and reading as level
    is the most honest thing a missing cell can look like.
    """
    azimuth = math.radians(LIGHT_AZIMUTH_DEG)
    altitude = math.radians(LIGHT_ALTITUDE_DEG)
    lx = math.sin(azimuth) * math.cos(altitude)
    ly = math.cos(azimuth) * math.cos(altitude)
    lz = math.sin(altitude)

    # Level ground lights at exactly `lz`; everything is expressed as a
    # departure from it, scaled so the extremes stay inside 0..1.
    spread = 2.0 * max(lz, 1.0 - lz)
    out: list[float] = []
    for row in range(window.rows):
        for col in range(window.cols):
            right = _height(window, col + 1, row)
            left = _height(window, col - 1, row)
            up = _height(window, col, row + 1)
            down = _height(window, col, row - 1)
            if right is None or left is None or up is None or down is None:
                out.append(0.5)
                continue
            east = right - left
            north = up - down
            # The surface normal of the cell, exaggerated, then dotted with the
            # lamp direction. Normalised so a flat cell reads as its own tilt
            # rather than as brightness.
            nx = -east * EXAGGERATION / (2 * window.cell_m)
            ny = -north * EXAGGERATION / (2 * window.cell_m)
            length = math.sqrt(nx * nx + ny * ny + 1.0)
            lit = (nx * lx + ny * ly + lz) / length
            out.append(round(max(0.0, min(1.0, 0.5 + (lit - lz) / spread)), 3))
    return out


def _height(window: TerrainWindow, col: int, row: int) -> float | None:
    """A cell's height, clamped to the edge, or None where it is unsurveyed."""
    col = max(0, min(window.cols - 1, col))
    row = max(0, min(window.rows - 1, row))
    value = window.heights[row * window.cols + col]
    return None if value != value else value


def crop_to(window: TerrainWindow, box: tuple[float, float, float, float],
            margin_m: float = 10.0) -> TerrainWindow:
    """The part of a window a plan actually shows.

    The window is 200 m because the shading needs the neighbours; the *drawing*
    is the garden, which is usually twenty. Sending the whole thing meant 39,999
    rectangles for a picture of about nine hundred — in a canvas that redraws on
    every pan.

    Cropped here rather than in the browser because the browser would still have
    to receive them.
    """
    min_x, min_y, max_x, max_y = box
    first_col = max(0, int((min_x - margin_m - window.min_x) / window.cell_m))
    first_row = max(0, int((min_y - margin_m - window.min_y) / window.cell_m))
    last_col = min(window.cols, int((max_x + margin_m - window.min_x) / window.cell_m) + 1)
    last_row = min(window.rows, int((max_y + margin_m - window.min_y) / window.cell_m) + 1)
    if last_col <= first_col or last_row <= first_row:
        return window

    heights = [
        window.heights[row * window.cols + col]
        for row in range(first_row, last_row)
        for col in range(first_col, last_col)
    ]
    return TerrainWindow(
        min_x=window.min_x + first_col * window.cell_m,
        min_y=window.min_y + first_row * window.cell_m,
        cell_m=window.cell_m,
        cols=last_col - first_col,
        rows=last_row - first_row,
        heights=heights,
        source=window.source,
        licence=window.licence,
        attribution=window.attribution,
        vertical_step_m=window.vertical_step_m,
    )
