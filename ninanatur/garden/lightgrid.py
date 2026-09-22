"""Sun hours across the whole garden, cell by cell.

The light model has answered at one point per bed — the polygon's centroid — so
a bed whose northern half sits in the house's shadow all day reported one number
from its middle. There was nothing to draw a map from and nothing to place a
plant by.

A grid is the same computation asked at many points, which only became
affordable once `solar/field.py` stopped redoing the sun and the shadows for
every one of them.
"""
from __future__ import annotations

import hashlib

import numpy as np

from ninanatur.garden.ground import lowest_ground, standing_on
from ninanatur.garden.lightcells import cells_of, roofs_of, surfaces_of
from ninanatur.garden.lightgrid_extent import CELL_LADDER_M as CELL_LADDER_M
from ninanatur.garden.lightgrid_extent import GRID_BUDGET_S as GRID_BUDGET_S
from ninanatur.garden.lightgrid_extent import GardenTooLarge as GardenTooLarge
from ninanatur.garden.lightgrid_extent import cell_size_for as cell_size_for
from ninanatur.garden.lightgrid_extent import check_extent as check_extent
from ninanatur.garden.lightgrid_extent import extent_of as extent_of
from ninanatur.garden.lightgrid_extent import grid_extent_of, grid_model, stands_in
from ninanatur.garden.lightgrid_model import LightGrid as LightGrid
from ninanatur.garden.models import Garden
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.climate import climate_at
from ninanatur.solar.light import MODEL_VERSION
from ninanatur.solar.position import Location
from ninanatur.solar.raster import Part, moments_for, parts_of

# The box and the cell size live in `lightgrid_extent` since 2026-09-21. The
# names are re-exported because this is where every caller has imported them.
from ninanatur.solar.reach import is_convex
from ninanatur.solar.relative import grid_sky_light
from ninanatur.solar.shading import Obstacle


def compute_grid(
    garden: Garden,
    obstacles: list[Obstacle],
    year: int = 2026,
    height_above_ground: float = 0.0,
    ground: TerrainWindow | None = None,
    horizon: list[float] | None = None,
    month: int | None = None,
) -> LightGrid | None:
    """Sun hours for every cell of the garden. None when there is nothing to
    cover: nothing drawn, or only streets.

    The garden: its plot, its beds and what the gardener drew, with a margin —
    `grid_extent_of`. The neighbours' houses are in `obstacles` and cast their
    shadows into it; the ground under them is not computed.

    `month` narrows the average from the whole March-to-October season to one
    month. A garden with a house on its south side is a different garden in
    April and in July, and one number for the season says neither.

    `ground` is the terrain under the garden, or None for the flat world every
    shadow in this project was computed in until Wave 17. With it, each cell is
    asked about at its own height and each obstacle stands on the ground beneath
    its footprint — so a neighbour's house uphill shades more than one on the
    level, and one downhill shades less.

    `horizon` is the ring from `geo/horizon.py`: what the land does beyond the
    plot. In flat country it changes next to nothing, because the ring sits
    below the altitude the model stops counting at (`MIN_ALTITUDE`). In a
    valley it decides whether the garden sees December at all.
    """
    box = grid_extent_of(garden)
    if box is None:
        return None
    min_x, min_y, max_x, max_y = box
    parts = parts_of(standing_on(obstacles, ground))
    cell = _cell_for(parts, box, terrain=ground is not None)
    width = max(max_x - min_x, 1.0)
    depth = max(max_y - min_y, 1.0)
    cols = max(1, int(width / cell) + 1)
    rows = max(1, int(depth / cell) + 1)

    floor = lowest_ground(ground, min_x, min_y, cell, cols, rows)
    grid = LightGrid(
        min_x=min_x, min_y=min_y, cell_m=cell, cols=cols, rows=rows, hours=[]
    )
    roofs = roofs_of(garden, ground)
    xs = [grid.centre_of(col, 0)[0] for col in range(cols)]
    ys = [grid.centre_of(0, row)[1] for row in range(rows)]
    surfaces = surfaces_of(xs, ys, ground, horizon, floor, roofs, height_above_ground)
    location = Location(latitude=garden.latitude, longitude=garden.longitude)
    # The sun and the sky together, in the garden's climate (doc 118).
    light = grid_sky_light(parts, moments_for(location, year, month),
                           cells_of(surfaces, xs, ys, cell),
                           climate_at(garden.latitude, garden.longitude))
    flat = [s for row in surfaces for s in row]

    def listed(values: np.ndarray, digits: int) -> list[float | None]:
        return [round(float(v), digits) if s.answered else None
                for s, v in zip(flat, values.ravel(), strict=True)]

    return LightGrid(
        min_x=min_x, min_y=min_y, cell_m=cell, cols=cols, rows=rows,
        hours=listed(light.morning + light.afternoon, 2), morning=listed(light.morning, 2),
        roof=[s.on_a_roof for s in flat], model=MODEL_VERSION,
        sky=listed(light.sky, 3), relative=listed(light.relative, 3),
        expected=listed(light.expected, 2),
    )


def _cell_for(parts: list[Part], box: tuple[float, float, float, float], *,
              terrain: bool) -> float:
    """The finest cell the budget buys over this box, once a box no cell could
    make affordable has been refused. What the raster pays for is parts, not
    obstacles (review, 2026-09-22), and a crown that drops its leaves makes it
    sweep the sky twice (doc 118)."""
    min_x, min_y, max_x, max_y = box
    near = sum(1 for p in parts if stands_in([(float(x), float(y)) for x, y in p.corners], box))
    deciduous = any(p.bare_transmission is not None for p in parts)
    check_extent(min_x, min_y, max_x, max_y, len(parts), near, terrain, deciduous)
    return cell_size_for(max(max_x - min_x, 1.0), max(max_y - min_y, 1.0), len(parts),
                         near, terrain, deciduous)


def _exact(element: object) -> str:
    """A mark on what casts a shadow from a concave outline. Its hull shaded the
    inner corner of every L-shaped house at every hour until 2026-09-22
    (`solar.reach`); marked, a map drawn before reads stale once, and only in a
    garden that has such a thing."""
    footprint = getattr(element, "footprint", [])
    casts = getattr(element, "height", None) is not None
    return "|exact" if casts and len(footprint) > 3 and not is_convex(footprint) else ""


def signature_of(
    garden: Garden, ground: object = None, horizon: object = None,
    *, shading_taxa: frozenset[int] | None = None,
) -> str:
    """A hash of everything that changes where the shadows fall.

    **Not a list of actions that ought to trigger a recomputation.** That was the
    first design and it is the wrong shape: such a list has to be extended by
    hand whenever a feature arrives, and forgetting is silent — a stale map that
    looks right. This is a fact about the inputs instead, so a new feature
    cannot forget to declare itself.

    What is in it: where the garden is, and every obstacle's kind, height, roof
    and outline, and every planting that casts a shadow, by species and position
    (`shading_taxa`; without it, every planting) — and **what the
    ground and the horizon were measured from** (Wave 25, doc 106). A state that
    gains a source is the case this last part is for: Bayern had no terrain at
    all until its tiles were read, and a garden whose map was computed flat
    would otherwise have stayed flat for ever, quietly. What is deliberately
    not: names, labels, colours, soil, bed membership — none of them move a
    shadow.

    And the grid's own shape: the rule for what it covers, its margin, ladder
    and budget (`grid_model`), and the box it covers. A map laid over another
    box is out of date even where no shadow moved — which is how every map
    stored before 2026-09-21, laid over the neighbours' land in 3 m cells, now
    says so and offers the finer one. The box is here rather than implied by the
    outlines because it also reads where an element came from: a neighbour's
    house the gardener makes their own joins it.
    """
    box = grid_extent_of(garden)
    parts: list[str] = [
        f"{garden.latitude:.5f},{garden.longitude:.5f}",
        grid_model(),
        "box|" + ("" if box is None else ",".join(f"{v:.2f}" for v in box)),
    ]
    # Where the ground came from and how finely it was measured: a better source
    # for the same place is a different map.
    whose = getattr(ground, "source", None)
    step = getattr(ground, "vertical_step_m", None)
    parts.append(f"ground|{whose}|{step}")
    ring = list(horizon) if isinstance(horizon, list) else []
    parts.append("horizon|" + ",".join(f"{angle:.2f}" for angle in ring))
    for element in sorted(
        list(garden.beds) + list(garden.obstacles), key=lambda e: e.element_id
    ):
        outline = ";".join(f"{x:.2f},{y:.2f}" for x, y in element.footprint) + _exact(element)
        parts.append(
            f"{element.element_id}|{element.kind}|{element.height}"
            f"|{element.roof}|{element.eaves_m}|{element.roof_fall_deg}"
            f"|{element.height_above_ground}|{outline}"
        )
        for planting in element.plantings:
            if shading_taxa is not None and planting.taxon_id not in shading_taxa:
                continue
            parts.append(
                f"p{planting.planting_id}|{planting.taxon_id}|{planting.quantity}"
                f"|{planting.x}|{planting.y}{'' if planting.x is None else '|at'}"
            )
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]
