"""What a light grid costs to compute — split out of `lightgrid_extent.py`.

The estimate the cell ladder is chosen by (`cell_size_for`, `check_extent`):
fitted to measurements and rounded up, so the budget it is held to stays a
promise rather than a hope. Its constants enter the grid's signature
(`cost_model`), so a map whose cell a different model chose reads stale.
"""
from __future__ import annotations

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


def estimate_ms(cells: float, parts: int, near: int | None = None,
                terrain: bool = False, deciduous: bool = False,
                tilted: bool = False, near_planes: int = 0, far_planes: int = 0) -> float:
    """What a grid of this many cells is expected to cost, in milliseconds.

    `parts` counts the convex parts of everything that casts, which is what
    the raster pays for: a neighbour of twenty-four corners is eight of them
    (review, 2026-09-22 — it counted obstacles until then). `near` counts the
    parts standing on the grid; the rest stand outside it. Unknown, every one
    is taken to stand on it — the dearer guess. `deciduous`: a crown drops its
    leaves, and the sky is swept a second time, bare. `tilted`: the cells have
    surfaces of their own — terrain, or a pitched roof — so every moment's
    beam is worked out per cell (doc 119). `near_planes` and `far_planes`
    count the roof planes the near and the far parts carry (doc 120).
    """
    near = parts if near is None else min(near, parts)
    far = parts - near
    sky = SKY_DIRECTIONS + (BARE_SKY_DIRECTIONS if deciduous else 0)
    swept = 1.0 + sky / SEASON_MOMENTS
    per_cell = CELL_COST_MS + CELL_NEAR_PART_MS * near + CELL_FAR_PART_MS * far
    raster = NEAR_PART_MS * near + FAR_PART_MS * far + cells * per_cell
    planes = near_planes + far_planes
    roofs = NEAR_PLANE_MS * near_planes + FAR_PLANE_MS * far_planes + cells * PLANE_CELL_MS * planes
    ground = cells * TERRAIN_CELL_MS if terrain else 0.0
    return (GRID_FIXED_MS + swept * (raster + roofs) + ground
            + (cells * TILTED_CELL_MS if tilted else 0.0))


def cost_model() -> str:
    """The estimate's constants, for the grid's signature (`grid_model`)."""
    return (f"cost {GRID_FIXED_MS},{NEAR_PART_MS},{FAR_PART_MS},"
            f"{CELL_COST_MS},{CELL_NEAR_PART_MS},{CELL_FAR_PART_MS},{TERRAIN_CELL_MS}"
            f"|sky {SKY_DIRECTIONS},{BARE_SKY_DIRECTIONS}/{SEASON_MOMENTS}|tilt {TILTED_CELL_MS}"
            f"|roof {NEAR_PLANE_MS},{FAR_PLANE_MS},{PLANE_CELL_MS}")


__all__ = ["cost_model", "estimate_ms"]
