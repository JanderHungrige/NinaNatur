"""Finding the trees nobody drew.

The single most common thing that shades a German garden is a large tree, and
until now one existed in this model only if somebody drew it. A neighbour's
beech is exactly the thing a person forgets, because it is not theirs.

The surface model already knows. What it does not know is *what* — a crown, a
hedge, a marquee and a badly-mapped building all read as "tall, and not ground".
So this proposes rather than decides: everything here becomes a suggestion the
gardener accepts or dismisses, with the same standing as Wave 16's misplacement
warning.

**No species.** No elevation product carries one, and the canopy model needs it —
a crown's transmission depends on whether it drops its leaves. A tree found here
falls to the existing default, broadleaf in leaf, which is stated rather than
hidden.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from ninanatur.geo.surface import SurfaceWindow

#: Below this it is a hedge, a car, a shed or a washing line.
#:
#: Three metres. Lower would fill a suburban garden with suggestions nobody
#: wants to dismiss one at a time, and a two-metre hedge shades almost nothing
#: at the sun angles this model counts.
MIN_HEIGHT_M = 3.0

#: Above this it is not a tree. The tallest broadleaf in Germany is about 45 m;
#: anything over this is a building the footprints missed, or noise.
MAX_HEIGHT_M = 45.0

#: Smallest crown worth proposing, in square metres. A 4 m² blob is a shrub, or
#: the corner of something the mask did not quite cover.
MIN_AREA_M2 = 6.0

#: Largest. Beyond this it is a row of trees, a wood, or a building — and a
#: single trunk position for a fifty-metre blob would be a fiction.
MAX_AREA_M2 = 300.0

#: How slender a crown may be before it is not a crown.
#:
#: A tree twenty metres tall with a crown 1.4 m across is a chimney, a mast, or
#: the corner of a building the mask did not cover — measured in Cologne, where
#: exactly those appeared. A Lombardy poplar is the honest exception and is rare
#: enough to lose.
SLENDER_RATIO = 8.0

#: How far from the garden a crown is still worth proposing.
#:
#: Fifty metres, the same reach the obstacle model already uses. A leafy Cologne
#: suburb yields 46 crowns in a 200 m window, and confirming 46 suggestions one
#: at a time is not a feature — the ones that can shade the garden are the ones
#: worth asking about.
WITHIN_M = 50.0

#: How far outside a known footprint a crown must start.
#:
#: Two metres. A roof and the tree beside it touch in a surface model, and
#: without a margin every building grows a small tree along its northern edge.
BUILDING_MARGIN_M = 2.0


@dataclass(frozen=True)
class Canopy:
    """Something tall that is not a building, and not yet in the garden."""

    #: Garden metres, at the middle of the crown.
    x: float
    y: float
    #: Half the crown's width, from its area. A crown is not a circle; this is
    #: the radius of the circle with the same area, which is what the shading
    #: model wants anyway.
    radius_m: float
    #: The tallest point of it.
    height_m: float


def canopies_in(
    window: SurfaceWindow,
    footprints: list[list[tuple[float, float]]],
    within_m: float = WITHIN_M,
) -> list[Canopy]:
    """Everything tall enough, thick enough, near enough and not a building.

    Ordered tallest first, because that is the order somebody wants to confirm
    them in: the tree that matters most is the one that shades most.
    """
    mask = _standing(window, footprints)
    found: list[Canopy] = []
    for blob in _blobs(mask, window.cols, window.rows):
        canopy = _describe(blob, window)
        if canopy is None:
            continue
        if math.hypot(canopy.x, canopy.y) > within_m:
            continue
        if canopy.radius_m * SLENDER_RATIO < canopy.height_m:
            continue
        found.append(canopy)
    found.sort(key=lambda c: c.height_m, reverse=True)
    return found


def _standing(
    window: SurfaceWindow, footprints: list[list[tuple[float, float]]]
) -> list[bool]:
    """Cells that are tall, real, and not on a building."""
    # The grown bounding boxes, computed once. Recomputing them per cell made
    # this twelve million polygon scans over a 400 x 400 window.
    boxes = _boxes(footprints)
    mask: list[bool] = []
    for row in range(window.rows):
        y = window.min_y + (row + 0.5) * window.cell_m
        for col in range(window.cols):
            x = window.min_x + (col + 0.5) * window.cell_m
            height = window.heights[row * window.cols + col]
            if math.isnan(height) or not MIN_HEIGHT_M <= height <= MAX_HEIGHT_M:
                mask.append(False)
                continue
            mask.append(not any(
                x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in boxes
            ))
    return mask


def _boxes(
    footprints: list[list[tuple[float, float]]]
) -> list[tuple[float, float, float, float]]:
    """Each footprint's bounding box, grown by the margin.

    A box rather than the outline: a roof and the tree beside it touch in a
    surface model, so the margin matters more than the shape does, and a garden
    has tens of buildings and a hundred and sixty thousand cells.
    """
    boxes: list[tuple[float, float, float, float]] = []
    for outline in footprints:
        if len(outline) < 3:
            continue
        xs = [p[0] for p in outline]
        ys = [p[1] for p in outline]
        boxes.append((
            min(xs) - BUILDING_MARGIN_M, min(ys) - BUILDING_MARGIN_M,
            max(xs) + BUILDING_MARGIN_M, max(ys) + BUILDING_MARGIN_M,
        ))
    return boxes


def _blobs(mask: list[bool], cols: int, rows: int) -> list[list[int]]:
    """Connected runs of standing cells, four-connected.

    Four rather than eight: two crowns touching at a single corner are two
    trees, and joining them would put one trunk between them.
    """
    seen = [False] * len(mask)
    out: list[list[int]] = []
    for start in range(len(mask)):
        if not mask[start] or seen[start]:
            continue
        blob: list[int] = []
        queue = deque([start])
        seen[start] = True
        while queue:
            here = queue.popleft()
            blob.append(here)
            row, col = divmod(here, cols)
            for r, c in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                if not (0 <= r < rows and 0 <= c < cols):
                    continue
                index = r * cols + c
                if mask[index] and not seen[index]:
                    seen[index] = True
                    queue.append(index)
        out.append(blob)
    return out


def _describe(blob: list[int], window: SurfaceWindow) -> Canopy | None:
    """One blob as a tree, or None if it is not one."""
    area = len(blob) * window.cell_m * window.cell_m
    if not MIN_AREA_M2 <= area <= MAX_AREA_M2:
        return None
    xs = 0.0
    ys = 0.0
    tallest = 0.0
    for index in blob:
        row, col = divmod(index, window.cols)
        xs += window.min_x + (col + 0.5) * window.cell_m
        ys += window.min_y + (row + 0.5) * window.cell_m
        tallest = max(tallest, window.heights[index])
    return Canopy(
        x=round(xs / len(blob), 1),
        y=round(ys / len(blob), 1),
        radius_m=round(math.sqrt(area / math.pi), 1),
        height_m=round(tallest, 1),
    )


__all__ = [
    "BUILDING_MARGIN_M",
    "MAX_AREA_M2",
    "MAX_HEIGHT_M",
    "MIN_AREA_M2",
    "MIN_HEIGHT_M",
    "SLENDER_RATIO",
    "WITHIN_M",
    "Canopy",
    "canopies_in",
]
