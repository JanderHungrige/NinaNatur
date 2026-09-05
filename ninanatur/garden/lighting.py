"""How much sun a planting site gets, and what stands in the way.

Split out of `store.py` in Wave 11. It is the one part of the store that is
about the sky rather than about rows, and `store.py` was over the file-length
limit before the element merge added to it.
"""
from __future__ import annotations

import sqlite3

from ninanatur.garden.canopies import (
    FIRST_LEAF_MONTH,
    deciduousness_of,
    transmission,
)
from ninanatur.garden.canopy import Canopy, canopy_of, shades
from ninanatur.garden.elements import now as _now
from ninanatur.garden.elements import polygon_centroid as _polygon_centroid
from ninanatur.garden.footprint import Shape, footprint_of
from ninanatur.garden.lightgrid import compute_grid, save_grid, signature_of
from ninanatur.garden.models import Garden
from ninanatur.garden.objects import ObjectKind, casts_shadow
from ninanatur.garden.roofs import Roof, shading_height
from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.light import bed_light_value, ellenberg_from_sun_hours
from ninanatur.solar.position import Location
from ninanatur.solar.shading import Obstacle as ShadingObstacle
from ninanatur.solar.shading import Point


def _planted_obstacles(
    conn: sqlite3.Connection, garden: Garden
) -> list[tuple[int, ShadingObstacle]]:
    """Woody plantings, as the shadows they will cast, tagged with their own bed.

    A bed is a marked area; a tree standing in it is not a different kind of bed,
    it is a thing that blocks the sun. The shading model already describes
    obstacles as vertical cylinders — the exact shape of a tree.

    **A tree now shades its own bed**, which it did not until this wave. The
    exclusion existed because a planting had no position: it sat at the bed's
    centroid, light was sampled at that same centroid, and one 2 m shrub in a
    16 m² bed took the bed from 12.6 sun hours to 0.0. That was an artifact of
    not knowing where the plant stood, not a fact about shade.

    Wave 15 gave clusters coordinates and Wave 16 samples a grid, so both halves
    of the artifact are gone: the tree stands where the gardener put it and
    darkens the cells it actually stands over. The bed's own value is the mean
    across its cells, so a shrub in a corner costs the corner and not the bed.

    A planting nobody has placed still falls back to the centroid, which is the
    honest guess and no longer a catastrophic one.
    """
    heights = _woody_heights(
        conn,
        [p.taxon_id for bed in garden.beds for p in bed.plantings if p.taxon_id is not None],
    )
    obstacles: list[tuple[int, ShadingObstacle]] = []
    for bed in garden.beds:
        centroid = _polygon_centroid(bed.polygon)
        for planting in bed.plantings:
            if planting.taxon_id is None:
                continue
            canopy = heights.get(planting.taxon_id)
            if not shades(canopy):
                continue
            assert canopy is not None  # narrowed by shades()
            # Where the gardener put the cluster, or the middle of the bed for
            # one nobody has moved.
            at = (
                (bed.x + planting.x, bed.y + planting.y)
                if planting.x is not None and planting.y is not None
                else centroid
            )
            # A crown, not a wall. What it passes depends on its leaves and on
            # the month — see `canopies.py` for where the numbers come from and
            # what is assumed where the catalogue says nothing.
            leaves = deciduousness_of(conn, planting.taxon_id)
            obstacles.append(
                (
                    bed.bed_id,
                    ShadingObstacle(
                        footprint=footprint_of(
                            shape=Shape.CIRCLE, x=at[0], y=at[1],
                            width=canopy.radius_m * 2, depth=None,
                            rotation=0.0, points=None,
                        ),
                        height=canopy.height_m,
                        transmission=transmission(leaves, FIRST_LEAF_MONTH),
                        bare_transmission=(
                            None
                            if leaves in ("evergreen", "variable")
                            else transmission(leaves, 1)
                        ),
                    ),
                )
            )
    return obstacles


def _woody_heights(
    conn: sqlite3.Connection, taxon_ids: list[int]
) -> dict[int, Canopy | None]:
    """Height and growth form for a set of species, in one query."""
    if not taxon_ids:
        return {}
    unique = sorted(set(taxon_ids))
    placeholders = ",".join("?" for _ in unique)
    rows = conn.execute(
        "SELECT taxon_id, trait_key, value_num, value_text FROM trait"
        f" WHERE taxon_id IN ({placeholders})"  # noqa: S608
        " AND trait_key IN ('height_max_m', 'growth_form')",
        unique,
    )
    heights: dict[int, float] = {}
    forms: dict[int, str] = {}
    for row in rows:
        tid = int(row["taxon_id"])
        if row["trait_key"] == "height_max_m" and row["value_num"] is not None:
            # Sources disagree and none overwrites another; the tallest recorded
            # value is the one that decides whether a shadow reaches a neighbour.
            heights[tid] = max(heights.get(tid, 0.0), float(row["value_num"]))
        elif row["value_text"] is not None:
            forms[tid] = str(row["value_text"])
    return {tid: canopy_of(heights.get(tid), forms.get(tid)) for tid in unique}


def _ground_under(conn: sqlite3.Connection, garden: Garden) -> TerrainWindow | None:
    """The stored terrain for this garden's location, or None.

    Read, never fetched. A recompute happens while somebody is waiting for the
    page, and a state survey answering in eight seconds is not something to do
    in that moment — the window is fetched when the garden is created and lives
    on the volume from then on. No window means the flat world, which is what
    every garden had until Wave 17 and what a garden in one of the nine states
    without a service keeps.
    """
    from ninanatur.geo.terrain_store import cache_key, load_window

    anchor = LatLon(lat=float(garden.latitude), lon=float(garden.longitude))
    return load_window(conn, cache_key(anchor))


def _horizon_around(conn: sqlite3.Connection, garden: Garden) -> list[float] | None:
    """The stored horizon ring for this location, or None.

    Read rather than fetched, for the same reason the window is. None and a flat
    ring are different things and only the ring is stored — a place nobody has
    measured is not the same as a place that turned out to be flat.
    """
    from ninanatur.geo.terrain_store import cache_key, load_horizon

    anchor = LatLon(lat=garden.latitude, lon=garden.longitude)
    return load_horizon(conn, cache_key(anchor))


def recompute_light(conn: sqlite3.Connection, garden_id: int) -> int:
    # Imported here rather than at module level: `store` imports this module, so
    # the other direction can only be a deferred one.
    from ninanatur.garden.store import load_garden

    """Recompute every bed's light from the garden's obstacles and its own trees.

    Returns beds updated.
    """
    garden = load_garden(conn, garden_id)
    obstacles = [
        ShadingObstacle(
            footprint=o.footprint,
            # The ridge is a line, not a wall. Without a roof shape this is the
            # recorded height, exactly as before.
            height=shading_height(o.height, Roof(o.roof), o.eaves_m),
        )
        for o in garden.obstacles
        # A height of None is an element nobody has said the height of. Treating
        # it as zero would be a claim; skipping it is the same answer Wave 8
        # gave for a building with no recorded height.
        if o.height is not None and casts_shadow(ObjectKind(o.kind))
    ]
    planted = _planted_obstacles(conn, garden)
    location = Location(latitude=garden.latitude, longitude=garden.longitude)
    ground = _ground_under(conn, garden)
    horizon = _horizon_around(conn, garden)

    # Everything that casts a shadow, including what grows in the beds. The
    # exclusion of a bed from its own plantings is gone — see
    # `_planted_obstacles` for why it existed and why it no longer has to.
    everything = obstacles + [o for _owner, o in planted]

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
            "UPDATE element SET ellenberg_l = ?, sun_hours = ?,"
            " light_computed_at = ? WHERE element_id = ?",
            (ellenberg_from_sun_hours(mean), round(mean, 2), _now(), bed.bed_id),
        )
        updated += 1
    conn.commit()
    return updated




def _relight_if_woody(conn: sqlite3.Connection, bed_id: int, taxon_id: int) -> None:
    """Recompute the garden's light when what was planted casts a shadow.

    Here rather than in the route, for the same reason the light computation
    itself lives in this module: the invariant has to hold whatever the entry
    point. Every unit test of planted shade called `recompute_light` itself and
    passed, while the running app left a bed at 12.6 h and Ellenberg 8 with a
    24 m oak standing in it.

    Skipped for anything under 1.5 m — recomputing a whole garden for a
    perennial is work that cannot change an answer.
    """
    canopy = _woody_heights(conn, [taxon_id]).get(taxon_id)
    if not shades(canopy):
        return
    row = conn.execute("SELECT garden_id FROM element WHERE element_id = ?", (bed_id,)).fetchone()
    if row is not None:
        recompute_light(conn, int(row["garden_id"]))


