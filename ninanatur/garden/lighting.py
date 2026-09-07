"""How much sun a planting site gets, and what stands in the way.

Split out of `store.py` in Wave 11. It is the one part of the store that is
about the sky rather than about rows, and `store.py` was over the file-length
limit before the element merge added to it.

**Nothing here runs on a write.** Every mutation used to relight the garden so
the plan could never disagree with its own obstacles, and that was right while a
garden was a handful of shapes. Wave 19 gave buildings real measured heights,
and the gardens people actually draw got big: 40 houses across 150 m, measured
here through the API on 2026-09-07, costs **2.5 s** per relight — against 3 ms
to store the bed. Drawing five beds meant waiting thirteen seconds for an answer
nobody had asked for yet.

So the light is recomputed when somebody asks: `POST /{token}/recompute` and
`POST /{token}/light`, both behind one button. The map already knew how to say
it was out of date — `LightGrid.stale` compares a signature of the shading
inputs rather than trusting anyone to remember what ought to have invalidated
it — so the honest half of this was already built. This change makes that flag
load-bearing instead of decorative.
"""
from __future__ import annotations

import sqlite3

from ninanatur.garden.elements import now as _now
from ninanatur.garden.elements import polygon_centroid as _polygon_centroid
from ninanatur.garden.lightgrid import compute_grid, signature_of
from ninanatur.garden.lightgrid_store import save_grid
from ninanatur.garden.lightview import (
    _ground_under,
    _horizon_around,
    shading_obstacles,
)
from ninanatur.garden.slopes import slope_at
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.light import bed_light_value, ellenberg_from_sun_hours
from ninanatur.solar.position import Location
from ninanatur.solar.shading import Point


def _fall_of(
    ground: TerrainWindow | None, bed: object
) -> tuple[float | None, float | None]:
    """How the ground under a bed falls, rounded to what can be defended.

    None without terrain, and None rather than zero: a stored zero would tell a
    gardener on a hillside that their garden is flat, which is exactly the claim
    this wave exists to stop making.

    A whole degree of slope and five of direction. The DGM1 states ± 0.3 m, and
    a tenth of a degree of aspect from that would be arithmetic rather than
    information.
    """
    if ground is None:
        return (None, None)
    outline = getattr(bed, "polygon", None) or []
    if not outline:
        return (None, None)
    x = sum(p[0] for p in outline) / len(outline)
    y = sum(p[1] for p in outline) / len(outline)
    slope, aspect = slope_at(ground, x, y)
    if slope <= 0.0:
        return (0.0, None)
    return (round(slope), round(aspect / 5.0) * 5.0)


def recompute_light(conn: sqlite3.Connection, garden_id: int) -> int:
    # Imported here rather than at module level: `store` imports this module, so
    # the other direction can only be a deferred one.
    from ninanatur.garden.store import load_garden

    """Recompute every bed's light from the garden's obstacles and its own trees.

    Returns beds updated.
    """
    garden = load_garden(conn, garden_id)
    location = Location(latitude=garden.latitude, longitude=garden.longitude)
    ground = _ground_under(conn, garden)
    horizon = _horizon_around(conn, garden)
    everything = shading_obstacles(conn, garden)

    # The grid, once for the garden. Raised beds are the exception: they need
    # their own field because the height changes every shadow polygon, and they
    # are rare enough that computing one extra grid per distinct height is
    # cheaper than the alternative of one field per point.
    grid = compute_grid(garden, everything, ground=ground, horizon=horizon)
    if grid is not None:
        save_grid(conn, garden_id, grid, signature_of(garden))

    updated = 0
    for bed in garden.beds:
        raised = bed.height_above_ground > 0
        mean = None if raised or grid is None else grid.mean_over(bed.polygon)
        if mean is None:
            # A raised bed, a bed narrower than a cell, or a garden with nothing
            # drawn. The point answer is still the honest fallback, and it is
            # what this whole model did until now.
            mean = bed_light_value(
                location,
                Point(*_polygon_centroid(bed.polygon)),
                everything,
                height_above_ground=bed.height_above_ground,
            ).sun_hours
        conn.execute(
            "UPDATE element SET ellenberg_l = ?, sun_hours = ?, slope_deg = ?,"
            " aspect_deg = ?,"
            " light_computed_at = ? WHERE element_id = ?",
            (
                ellenberg_from_sun_hours(mean),
                round(mean, 2),
                *_fall_of(ground, bed),
                _now(),
                bed.bed_id,
            ),
        )
        updated += 1
    conn.commit()
    return updated




