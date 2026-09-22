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
from typing import Any

from ninanatur.garden.elements import now as _now
from ninanatur.garden.elements import polygon_centroid as _polygon_centroid
from ninanatur.garden.footprint import covers
from ninanatur.garden.lightgrid import LightGrid, compute_grid, signature_of
from ninanatur.garden.lightgrid_store import save_grid
from ninanatur.garden.lightview import (
    _ground_under,
    _horizon_around,
    shading_obstacles,
    shading_taxa,
)
from ninanatur.garden.models import Element, Garden
from ninanatur.garden.objects import ObjectKind, symbol_of
from ninanatur.garden.slopes import slope_at
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.light import light_value
from ninanatur.solar.position import Location
from ninanatur.solar.shading import Obstacle, Point


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


def _is_built(kind: str) -> bool:
    try:
        return symbol_of(ObjectKind(kind)) in ("building", "masonry")
    except ValueError:
        return False


def _open_point(outline: list[list[float]], garden: Garden) -> Point:
    """Where to sample a bed that has no cells of its own: its middle, unless
    something built stands there. A border drawn across a map house's wall line
    had its middle inside the house, and the ground under a house — where the
    sun never reaches — was stored as its light: 0 h, deep shade, for a border
    in full sun (review, 2026-09-21). Then the first of its edges' middles and
    its corners that is in the open; the middle if none is.
    """
    built = [e.footprint for e in garden.obstacles if _is_built(e.kind)]
    middle = _polygon_centroid(outline)
    ring = [(float(p[0]), float(p[1])) for p in outline]
    halves = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
              for a, b in zip(ring, ring[1:] + ring[:1], strict=True)]
    for point in [middle, *halves, *ring]:
        if not any(len(f) >= 3 and covers(f, point) for f in built):
            return Point(*point)
    return Point(*middle)


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
        save_grid(conn, garden_id, grid, signature_of(
            garden, ground, horizon, shading_taxa=shading_taxa(conn, garden)))
    else:
        # Nothing left to cover: a map stored earlier describes a garden that
        # is gone, and kept, it said "stale" after every press of the button.
        conn.execute("DELETE FROM light_grid WHERE garden_id = ?", (garden_id,))

    updated = 0
    fallback = _PointLight(everything, location, ground, horizon)
    for bed in garden.beds:
        hours, sky, relative, expected = _bed_light(grid, bed, garden, fallback)
        conn.execute(
            "UPDATE element SET ellenberg_l = ?, sun_hours = ?, slope_deg = ?,"
            " aspect_deg = ?, sky_view = ?, relative_light = ?, expected_sun_h = ?,"
            " light_computed_at = ? WHERE element_id = ?",
            (
                # From the hours and the sky as stored, so they always agree.
                light_value(round(hours, 2), _rounded(sky, 3)),
                round(hours, 2),
                *_fall_of(ground, bed),
                _rounded(sky, 3), _rounded(relative, 3), _rounded(expected, 2),
                _now(),
                bed.bed_id,
            ),
        )
        updated += 1
    conn.commit()
    return updated


def _rounded(value: float | None, digits: int) -> float | None:
    return None if value is None else round(value, digits)


class _PointLight:
    """The one-point answer, for a bed the grid cannot: its moments, parts and
    climate worked out once for all of a garden's beds that need it.

    Asked as a cell of the grid is asked (`lightcells.surface_at`): the point
    at its own ground plus the bed's height, the obstacles each on the ground
    under it, the sky through the point's own slope and the hills beyond. It
    stood on flat ground under an open horizon until 2026-09-22, and a narrow
    bed in a valley saw a sky its neighbouring cells did not (review)."""

    def __init__(self, obstacles: list[Obstacle], location: Location,
                 ground: TerrainWindow | None = None,
                 horizon: list[float] | None = None) -> None:
        self.obstacles, self.location = obstacles, location
        self.ground, self.horizon = ground, horizon
        self._ready: tuple[Any, Any, Any] | None = None
        # The grid's rings are rounded to a step of slope and aspect and shared
        # (`lightcells._ring`); a point's are rounded the same way.
        self._rings: dict[tuple[float, float], tuple[float, ...]] = {}

    def at(self, x: float, y: float, height: float) -> tuple[float, float, float, float]:
        from ninanatur.garden.ground import standing_on
        from ninanatur.garden.lightcells import surface_at
        from ninanatur.solar.climate import climate_at
        from ninanatur.solar.raster import LEVEL, moments_for, parts_of, plane_of
        from ninanatur.solar.relative import point_sky_light

        if self._ready is None:
            self._ready = (parts_of(standing_on(self.obstacles, self.ground)),
                           moments_for(self.location),
                           climate_at(self.location.latitude, self.location.longitude))
        parts, moments, climate = self._ready
        # A hole in the survey stands on the lowest ground there is, as a
        # cell's does (`ground.height_at`).
        floor = min(self.ground.heights) if self.ground and self.ground.heights else 0.0
        surface = surface_at((x, y), self.ground, self.horizon, floor, [], height, self._rings)
        # A raised bed is a box: its soil lies level however the ground under it
        # falls, though the hillside still stands between it and the low sun,
        # which is its ring (review, 2026-09-22).
        plane = LEVEL if height > 0 else plane_of(surface.slope, surface.aspect)
        light = point_sky_light(parts, moments, climate, x, y, surface.z,
                                list(surface.ring) or None, plane=plane)
        return (float(light.morning[0] + light.afternoon[0]), float(light.sky[0]),
                float(light.relative[0]), float(light.expected[0]))


def _bed_light(grid: LightGrid | None, bed: Element, garden: Garden, fallback: _PointLight,
               ) -> tuple[float, float | None, float | None, float | None]:
    """A bed's sun hours, sky, relative illuminance and expected hours: the
    mean of its cells, or — a raised bed, a bed narrower than a cell, a garden
    with nothing drawn — the honest one-point answer this model always gave."""
    if bed.height_above_ground <= 0 and grid is not None:
        hours = grid.mean_over(bed.polygon)
        if hours is not None:
            return (hours, grid.mean_over(bed.polygon, grid.sky),
                    grid.mean_over(bed.polygon, grid.relative),
                    grid.mean_over(bed.polygon, grid.expected))
    point = _open_point(bed.polygon, garden)
    return fallback.at(point.x, point.y, bed.height_above_ground)
