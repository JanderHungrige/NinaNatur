"""What a light grid costs to compute — split out of `lightgrid_extent.py`.

The estimate the cell ladder is chosen by (`cell_size_for`, `check_extent`):
fitted to measurements and rounded up, so the budget it is held to stays a
promise rather than a hope. Its constants enter the grid's signature
(`cost_model`), so a map whose cell a different model chose reads stale.
"""
from __future__ import annotations

import math

#: What a grid costs since the raster (Wave 26, doc 117), fitted to end-to-end
#: measurements on 2026-09-22 and rounded up so the estimate stays above them.
#: What costs is each convex part (`solar.convex_parts`) asked about at every
#: moment — a part standing on the grid at all of them, a neighbour's outside
#: it only while its long shadows reach in — and, far less, the cells under
#: its shadow. Forty rectangular neighbours round a 35 x 50 m plot: 1.1 s at
#: 0.5 m, where the field took five for 1 m. Forty of twenty-four corners
#: (358 parts): 7.8 s at any cell, which is what the estimate says too.
#: Until Wave 26: 0.1 ms a cell plus 0.05 ms a cell for each obstacle.
GRID_FIXED_MS = 230.0
NEAR_PART_MS = 95.0
FAR_PART_MS = 15.0
CELL_COST_MS = 0.008
CELL_NEAR_PART_MS = 0.002
CELL_FAR_PART_MS = 0.0008
#: What terrain adds to each cell: its height, its slope and the ring they
#: give, worked out in Python before the raster starts (0.006 ms measured,
#: with the rings shared).
TERRAIN_CELL_MS = 0.01
#: The sky beside the sun (doc 118). The part and cell terms above were fitted
#: to the sun's moments alone — 3,846 in a Wuppertal season — and grow with
#: what is swept: Reinhart's 577 patches for the sky a map shows, and where a
#: crown drops its leaves Tregenza's 145 for the season's bare months.
SEASON_MOMENTS = 3846
SKY_DIRECTIONS = 577
BARE_SKY_DIRECTIONS = 145
#: What weighing each moment by what its beam brings costs (doc 119): nothing
#: worth counting where every cell is level, since the beam is then one number
#: a moment. Where a cell has a surface of its own — the ground's fall, or a
#: roof's pitch — the cosine is worked out per cell at every moment, and that
#: is a cost per cell and not per part: 0.018 ms measured at 4,800 cells (88 ms)
#: and at 48,841 (840 ms), rounded up like the rest.
TILTED_CELL_MS = 0.02
#: What one of a roof's planes costs (doc 120): about what a wall does, since
#: each is a cut of the ray at every moment the part is asked about — so per
#: plane, near or far like the part that carries it, and only a little per
#: cell, where a leaning plane is cut against each cell's own height. Fitted on
#: 36 houses as blocks against the same 36 as gables and hips, at forced cells
#: from 5 m to 0.5 m (review, 2026-09-28): 17–18 ms a plane on the plot, 9–10
#: ms round it, 0.0007 ms a cell a plane — given here without the sky's share,
#: which the estimate adds. Priced per cell alone, 36 hipped houses were
#: estimated at 4.7 s and took 7.1.
NEAR_PLANE_MS = 17.0
FAR_PLANE_MS = 10.0
PLANE_CELL_MS = 0.0007
#: A crown (doc 121) standing on the grid is priced as the part it is. Its
#: chord is a quadratic solved at each cell under the ellipse it throws —
#: fewer cells than a part's square swept from the ground — and it costs less
#: than a part: measured on 12 and 36 drawn trees on a 94 m plot at forced
#: cells from 2 m to 0.5 m (2026-09-28), about 71 ms a crown and 0.0008 ms a
#: cell against a part's 95 and 0.002 — 36 trees took 4.8 s at 0.5 m where the
#: estimate says 8.4, and 3.2 s at 2 m where it says 4.6.
#:
#: Off the grid it costs more than a far part: a crown just past the grid's
#: edge throws its shadow in at most moments, not only while shadows are long.
#: 24 trees 12 m outside the plot took 0.96 s at 2 m where the far price said
#: 0.75 (review, 2026-09-28) — about 24 ms a crown, so a far crown adds this
#: to its part's, rounded up; from 20 m out the far price held alone.
#: `python -m scripts.measure_crown_cost` prints both.
FAR_CROWN_MS = 15.0
#: And a crown asks about more cells the further the grid's cells stand apart
#: in height: the grid sizes each crown's box from the lowest cell to the
#: highest, so a slope — or a roof on the plot, of any shape — stretches every
#: crown's box towards the sun by the height between them. Priced by that
#: height (`lightgrid_load.relief_of`), not by what raises it: keyed on
#: "terrain" and "pitched planes", level surveyed ground paid for a slope and
#: a 15 m house of no known shape paid nothing (review of 45eb56a). And per
#: crown by the cell's size, not by the grid's count of cells: the stretch is
#: a stretch in metres, so its cells go with 1/cell², and priced per cell of
#: the grid a 24 × 40 m garden was estimated under what it took, two of them
#: past the budget (review of 596a89f). Measured by difference — trees and a
#: house, less the trees, less the house — per crown and metre of height:
#: 1.4, 4.7 and 17.7 ms at 2, 1 and 0.5 m on a 94 m plot, about a millisecond
#: plus 4.3/cell². On a 24 × 40 m plot the second part came to 0.56 of that at
#: every cell: a smaller grid clips the stretched boxes, taken here as its
#: width over `RELIEF_REACH_M`. Rounded up; `scripts.measure_crown_cost`.
CROWN_RELIEF_MS = 1.0
CROWN_RELIEF_M2_MS = 4.5
RELIEF_REACH_M = 60.0
#: And a neighbour just off the grid throws its shadow in at most moments,
#: not only while shadows are long: 36 houses from the map with their near
#: walls 1 to 9 m outside the grid took 1.8 s at 2 m cells where the far price
#: said 1.0; from 11 m out the far price held with room. A part standing
#: within its own height of the grid (`lightgrid_load.REACH_ALTITUDE_DEG`),
#: measured from its lowest cell as the raster measures it, adds this to the
#: far price: 21 ms a house measured, rounded up by a third. (35 at first,
#: sized to a review's run of 2.3 s taken while other runs shared the
#: machine; it moved a dense suburban garden from 1 m cells to 2 m for
#: nothing — review of 45eb56a.) `python -m scripts.measure_neighbour_cost`.
REACH_PART_MS = 28.0


def estimate_ms(cells: float, parts: int, near: int | None = None,
                terrain: bool = False, deciduous: bool = False,
                tilted: bool = False, near_planes: int = 0, far_planes: int = 0,
                *, far_crowns: int = 0, near_crowns: int = 0, reaching: int = 0,
                relief_m: float = 0.0, cell_m: float = 1.0) -> float:
    """What a grid of this many cells is expected to cost, in milliseconds.

    `parts` counts the convex parts of everything that casts, which is what
    the raster pays for: a neighbour of twenty-four corners is eight of them
    (review, 2026-09-22 — it counted obstacles until then). `near` counts the
    parts standing on the grid; the rest stand outside it. Unknown, every one
    is taken to stand on it — the dearer guess. `deciduous`: a crown drops its
    leaves, and the sky is swept a second time, bare. `tilted`: the cells have
    surfaces of their own — terrain, or a pitched roof — so every moment's
    beam is worked out per cell (doc 119). `near_planes` and `far_planes`
    count the roof planes the near and the far parts carry (doc 120),
    `far_crowns` and `near_crowns` the parts off and on the grid that are
    crowns (doc 121), `relief_m` how far the grid's cells stand apart in
    height, and `reaching` the neighbours within their height of the grid.
    `cell_m` is the cell's size, which a stretch in metres is counted in.
    """
    near = parts if near is None else min(near, parts)
    far = parts - near
    sky = SKY_DIRECTIONS + (BARE_SKY_DIRECTIONS if deciduous else 0)
    swept = 1.0 + sky / SEASON_MOMENTS
    per_cell = CELL_COST_MS + CELL_NEAR_PART_MS * near + CELL_FAR_PART_MS * far
    raster = NEAR_PART_MS * near + FAR_PART_MS * far + REACH_PART_MS * reaching + cells * per_cell
    planes = near_planes + far_planes
    roofs = NEAR_PLANE_MS * near_planes + FAR_PLANE_MS * far_planes + cells * PLANE_CELL_MS * planes
    clipped = min(1.0, math.sqrt(cells) * cell_m / RELIEF_REACH_M)
    stretched = CROWN_RELIEF_MS + CROWN_RELIEF_M2_MS / cell_m**2 * clipped
    crowns = FAR_CROWN_MS * far_crowns + near_crowns * relief_m * stretched
    ground = cells * TERRAIN_CELL_MS if terrain else 0.0
    return (GRID_FIXED_MS + swept * (raster + roofs + crowns) + ground
            + (cells * TILTED_CELL_MS if tilted else 0.0))


def cost_model() -> str:
    """The estimate's constants, for the grid's signature (`grid_model`)."""
    return (f"cost {GRID_FIXED_MS},{NEAR_PART_MS},{FAR_PART_MS},"
            f"{CELL_COST_MS},{CELL_NEAR_PART_MS},{CELL_FAR_PART_MS},{TERRAIN_CELL_MS}"
            f"|sky {SKY_DIRECTIONS},{BARE_SKY_DIRECTIONS}/{SEASON_MOMENTS}|tilt {TILTED_CELL_MS}"
            f"|roof {NEAR_PLANE_MS},{FAR_PLANE_MS},{PLANE_CELL_MS}"
            f"|crown {FAR_CROWN_MS},{CROWN_RELIEF_MS},{CROWN_RELIEF_M2_MS},{RELIEF_REACH_M}"
            f"|reach {REACH_PART_MS}")


__all__ = ["cost_model", "estimate_ms"]
