"""What the light grid covers, and how fine its cells are.

Split out of `lightgrid.py` on 2026-09-21, when the grid stopped covering
everything on the plan and the rule for what it does cover needed room. The
arithmetic of the cells stayed there; this is the box they are laid over and
the size they come in, which are one question: the smaller the box, the finer
the cells the same wait can buy.
"""
from __future__ import annotations

from ninanatur.garden.models import Element, Garden
from ninanatur.garden.objects import ObjectKind

#: Cell sizes to choose from, finest first. A garden is measured in metres and a
#: gardener thinks in them; anything below half a metre says more than the model
#: knows, given that most building heights are assumed and a roof pitch is
#: inferred from a rectangle.
CELL_LADDER_M: tuple[float, ...] = (0.5, 1.0, 2.0, 3.0, 5.0)

#: Seconds the recompute may spend on the grid.
#:
#: It was a flat cap of 600 cells, chosen when every write recomputed the light
#: and half a second was the whole budget. Nothing recomputes on a write any
#: more — it happens when somebody presses a button knowing it will take a
#: moment — so the limit can be what it should always have been: a time, not a
#: count.
#:
#: A count was the wrong shape anyway, because a cell is not a fixed price. It
#: costs what the obstacles around it cost. Measured on 2026-09-07: 0.24 ms in a
#: garden with three buildings and 1.9 ms in one with forty, which a single
#: number has to be wrong about at one end or the other. At 600 cells a small
#: garden waited 0.16 s for a 1 m grid it did not need to be that coarse.
GRID_BUDGET_S = 5.0

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

#: Metres of ground shown past the garden itself. Enough for the strip along
#: the fence and the shadow a hedge throws over it; not the neighbours' land.
GRID_MARGIN_M = 5.0

#: Which rule `grid_extent_of` follows: 1 was everything on the plan, 2 is the
#: garden and its margin. Raise it whenever the rule changes. The signature
#: carries it, so every stored map then says it is out of date instead of
#: quietly keeping the old rule's grid.
EXTENT_RULE = 2


class GardenTooLarge(ValueError):
    """A garden whose light grid cannot be computed in any reasonable time.

    A ValueError, so the API's one backstop turns it into a 422 with its reason
    rather than a 500 — or, as before this existed, no answer at all.
    """


#: How far past the grid budget a garden may go before it is refused outright.
#: `cell_size_for` stops at its coarsest cell and simply runs long beyond that;
#: a little over is a slow button, far over is a request that never returns.
REFUSE_AT_BUDGET_MULTIPLE = 4.0

#: The most cells a grid may have at the coarsest rung. The raster computes a
#: large grid quickly (doc 117) — four kilometres square at 5 m in seconds —
#: but a map is a list of cells kept in the database and sent to the page, and
#: time alone stopped refusing a garden with a shed drawn two kilometres out.
#: The largest legitimate garden, 1.2 km square, needs 58,000.
MAX_CELLS = 100_000


def estimate_ms(cells: float, parts: int, near: int | None = None,
                terrain: bool = False, deciduous: bool = False) -> float:
    """What a grid of this many cells is expected to cost, in milliseconds.

    `parts` counts the convex parts of everything that casts, which is what
    the raster pays for: a neighbour of twenty-four corners is eight of them
    (review, 2026-09-22 — it counted obstacles until then). `near` counts the
    parts standing on the grid; the rest stand outside it. Unknown, every one
    is taken to stand on it — the dearer guess. `deciduous`: a crown drops its
    leaves, and the sky is swept a second time, bare.
    """
    near = parts if near is None else min(near, parts)
    far = parts - near
    sky = SKY_DIRECTIONS + (BARE_SKY_DIRECTIONS if deciduous else 0)
    swept = 1.0 + sky / SEASON_MOMENTS
    per_cell = CELL_COST_MS + CELL_NEAR_PART_MS * near + CELL_FAR_PART_MS * far
    raster = NEAR_PART_MS * near + FAR_PART_MS * far + cells * per_cell
    return GRID_FIXED_MS + swept * raster + (cells * TERRAIN_CELL_MS if terrain else 0.0)


def stands_in(footprint: list[tuple[float, float]],
              box: tuple[float, float, float, float]) -> bool:
    """Whether a footprint reaches into the grid's box: its shadow is then on
    the grid at every moment, which is what a grid pays for (`estimate_ms`)."""
    xs = [x for x, _ in footprint]
    ys = [y for _, y in footprint]
    return bool(xs) and max(xs) >= box[0] and min(xs) <= box[2] \
        and max(ys) >= box[1] and min(ys) <= box[3]


def cells_at(width_m: float, depth_m: float, cell: float) -> float:
    """How many cells a box is cut into at this size, as `compute_grid` cuts it."""
    return (int(width_m / cell) + 1) * (int(depth_m / cell) + 1)


def check_extent(
    min_x: float, min_y: float, max_x: float, max_y: float, parts: int = 0,
    near: int | None = None, terrain: bool = False, deciduous: bool = False,
) -> None:
    """Refuse a garden whose grid would take far longer than the budget allows.

    The second line of defence, behind the API's coordinate bounds. It asks the
    same question `cell_size_for` does — what the grid will cost — at the
    coarsest cell the ladder has, so the limit is the budget rather than a
    second number somebody has to keep in step with it.

    Asked about the box the grid will actually cover (`grid_extent_of`), not the
    whole plan: a street running a kilometre past the garden is not computed,
    so it is no reason to refuse.

    Reproduced before it existed: one obstacle at x = 1e9 made the grid a
    billion metres wide, and `POST /light` did not come back.
    """
    width = max(max_x - min_x, 1.0)
    depth = max(max_y - min_y, 1.0)
    cells = cells_at(width, depth, CELL_LADDER_M[-1])
    if cells > MAX_CELLS or (estimate_ms(cells, parts, near, terrain, deciduous) / 1000
                             > GRID_BUDGET_S * REFUSE_AT_BUDGET_MULTIPLE):
        raise GardenTooLarge(
            f"Garten zu groß: {width:.0f} × {depth:.0f} m lassen sich nicht in "
            f"vertretbarer Zeit berechnen"
        )


def cell_size_for(width_m: float, depth_m: float, parts: int = 0,
                  near: int | None = None, terrain: bool = False,
                  deciduous: bool = False) -> float:
    """The finest cell that keeps the recompute inside `GRID_BUDGET_S`.

    Since the raster (doc 117) nearly every garden gets 0.5 m: forty
    neighbours round an ordinary plot cost 1.4 s. A plot with forty houses
    drawn on it, or a very large one, still steps down the ladder, which is the
    point of asking about time rather than about a cell count.
    """
    for cell in CELL_LADDER_M:
        cells = cells_at(width_m, depth_m, cell)
        # The cap on the grid that is built, not only the coarsest: a map is a
        # list kept and sent, and cheap cells let a plain 500 m plot reach a
        # million of them (review, 2026-09-22).
        if cells <= MAX_CELLS and estimate_ms(cells, parts, near, terrain, deciduous) \
                <= GRID_BUDGET_S * 1000:
            return cell
    return CELL_LADDER_M[-1]


def extent_of(garden: Garden) -> tuple[float, float, float, float] | None:
    """(min_x, min_y, max_x, max_y) over everything drawn, or None if nothing is.

    Everything, streets and neighbours included. The relief under the plan is
    cropped to this (`GET /terrain`); the light grid covers less — see
    `grid_extent_of`.
    """
    points: list[tuple[float, float]] = []
    for element in list(garden.beds) + list(garden.obstacles):
        points.extend(element.footprint)
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _stands_up(element: Element) -> bool:
    """Something with a height that is neither the plot nor a street."""
    return element.height is not None and element.kind not in (
        ObjectKind.GARDEN, ObjectKind.STREET
    )


def _drawn_by_hand(element: Element) -> bool:
    """Nobody but the gardener has said anything about it.

    The map import writes `roof_source = 'osm'` on every house it brings, and a
    survey writes its own source into both fields — only ever over a height the
    gardener did not type (`measured.apply`). The drawing tools leave both at
    the schema's default, `user`. An accepted tree from the laser survey says
    `measured` and counts as found, like the neighbours: where it stands on the
    plot, the plot covers it anyway.

    What it gets wrong: a neighbour's house saved through the element form
    before Wave 21, which wrote `user` into the height on every save, reads as
    drawn — and widens the grid as every house did before.
    """
    return element.height_source == "user" and element.roof_source == "user"


def grid_extent_of(garden: Garden) -> tuple[float, float, float, float] | None:
    """(min_x, min_y, max_x, max_y) of the ground the light grid covers.

    The garden and a strip around it, not the neighbourhood. It was `extent_of`,
    everything on the plan — and a garden made from the map has the neighbours'
    houses on it up to 50 m out and every street at its full length, so a
    25 x 40 m plot became a grid of 200 x 115 m or more, and the time budget
    gave it 3 to 5 m cells. The owner's check on 2026-09-21: the shade is not
    fine enough, the raster too large. The plot and 5 m is 35 x 50 m: 1 m cells
    in the same five seconds.

    Covered: the plot outline, every bed wherever it is, and whatever the
    gardener drew that stands up, with `GRID_MARGIN_M` around the lot. Left out:
    streets, anything without a height, and what the import or a survey brought.
    The neighbours' houses still cast their shadows — they stay in the obstacles
    `compute_grid` is handed — and only the cells over their land go.

    A garden without a plot has nothing that tells its ground from the
    neighbours', so there every standing element counts, imported or not, and
    no margin is added: those are mostly gardens drawn by hand, whose outermost
    house or hedge already is the edge, and 5 m more on every side would have
    doubled a small garden's cells and pushed a crowded one off the 0.5 m rung.
    And where it holds nothing that stands up either — a lawn, a path, paving —
    those surfaces are the garden, and they are what is covered. Only a garden
    of streets alone has no grid.
    """
    plots = [e for e in garden.obstacles if e.kind == ObjectKind.GARDEN]
    standing = [e for e in garden.obstacles if _stands_up(e)]
    if not plots:
        return _bounds(garden.beds + standing, 0.0) or _bounds(
            [e for e in garden.obstacles if e.kind != ObjectKind.STREET], 0.0)
    drawn = [e for e in standing if _drawn_by_hand(e)]
    return _bounds(plots + garden.beds + drawn, GRID_MARGIN_M)


def _bounds(
    elements: list[Element], margin: float
) -> tuple[float, float, float, float] | None:
    points = [p for e in elements for p in e.footprint]
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin)


def grid_model() -> str:
    """Everything besides the garden that decides the grid's shape.

    Folded into the signature, so a map computed under another rule, margin,
    ladder or budget reads as stale and the button offers the new grid.
    """
    from ninanatur.solar.light import MODEL_VERSION

    return (
        f"grid|rule {EXTENT_RULE}|margin {GRID_MARGIN_M}|ladder {CELL_LADDER_M}"
        f"|budget {GRID_BUDGET_S}|cost {GRID_FIXED_MS},{NEAR_PART_MS},{FAR_PART_MS},"
        f"{CELL_COST_MS},{CELL_NEAR_PART_MS},{CELL_FAR_PART_MS},{TERRAIN_CELL_MS}"
        f"|sky {SKY_DIRECTIONS},{BARE_SKY_DIRECTIONS}/{SEASON_MOMENTS}"
        f"|model {MODEL_VERSION}"
    )
