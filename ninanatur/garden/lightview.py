"""Describing a garden to the light model, and asking it something.

Split out of `lighting.py` on 2026-09-07, when the month view pushed that file
past the length limit. The seam is the useful one rather than the convenient
one: this module turns a garden into the obstacles, ground and sky the solar
code wants, and answers a question with them. `lighting.py` is what takes such
an answer and *stores* it.

So the dependency runs one way — `lighting` imports this, never the reverse.
"""
from __future__ import annotations

import sqlite3

from ninanatur.garden.canopies import (
    FIRST_LEAF_MONTH,
    deciduousness_of,
    transmission,
)
from ninanatur.garden.canopy import Canopy, canopy_of, shades
from ninanatur.garden.elements import polygon_centroid as _polygon_centroid
from ninanatur.garden.footprint import Shape, footprint_of
from ninanatur.garden.lightgrid import LightGrid, compute_grid
from ninanatur.garden.models import Garden
from ninanatur.garden.objects import ObjectKind, casts_shadow
from ninanatur.garden.roofs import Roof, shading_height
from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.shading import Obstacle as ShadingObstacle


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
    from ninanatur.garden.terrain_sync import ground_for

    anchor = LatLon(lat=float(garden.latitude), lon=float(garden.longitude))
    return ground_for(conn, anchor)


def _horizon_around(conn: sqlite3.Connection, garden: Garden) -> list[float] | None:
    """The stored horizon ring for this location, or None.

    Read rather than fetched, for the same reason the window is. None and a flat
    ring are different things and only the ring is stored — a place nobody has
    measured is not the same as a place that turned out to be flat.
    """
    from ninanatur.garden.terrain_sync import horizon_for

    anchor = LatLon(lat=garden.latitude, lon=garden.longitude)
    return horizon_for(conn, anchor)


def shading_obstacles(
    conn: sqlite3.Connection, garden: Garden
) -> list[ShadingObstacle]:
    """Everything in this garden that stands between a point and the sun.

    Includes what grows in the beds. The exclusion of a bed from its own
    plantings is gone — see `_planted_obstacles` for why it existed and why it
    no longer has to.
    """
    built = [
        ShadingObstacle(
            footprint=o.footprint,
            # The ridge is a line, not a wall. Without a roof shape this is the
            # recorded height, exactly as before.
            height=shading_height(o.height, Roof(o.roof), o.eaves_m),
            # So a point on this building's own roof can leave it out.
            owner=o.element_id,
        )
        for o in garden.obstacles
        # A height of None is an element nobody has said the height of. Treating
        # it as zero would be a claim; skipping it is the same answer Wave 8
        # gave for a building with no recorded height.
        if o.height is not None and casts_shadow(ObjectKind(o.kind))
    ]
    return built + [o for _owner, o in _planted_obstacles(conn, garden)]


def month_grid(
    conn: sqlite3.Connection, garden: Garden, month: int
) -> LightGrid | None:
    """One month's light across the garden, computed now and not stored.

    A view rather than a second stored map. The season average is the number a
    plant is placed by, and it is what the button computes and keeps; a month is
    a question somebody asks while looking — *does that corner see anything in
    March* — and it is answered from the same inputs at about a quarter of the
    cost, because a month is sampled six times where the season is sampled
    twenty-five.

    Measured on a garden with a house on its south side: the season reports a
    median of 10.6 h, March 7.3 h and June 14.8 h. One number for the season
    describes neither, and it is the March figure a gardener needs before
    putting anything early-flowering in that corner.

    Storing eight of them was the alternative and it is the wrong trade: it
    multiplies the one slow operation in this app by eight to answer a question
    most gardens are never asked.
    """
    return compute_grid(
        garden,
        shading_obstacles(conn, garden),
        ground=_ground_under(conn, garden),
        horizon=_horizon_around(conn, garden),
        month=month,
    )
