"""What the light endpoints answer with.

Split from `api/light.py` on 2026-09-21: that module had grown to 350 lines,
past the project's limit, with its response shapes and its routes in one file.
The names are unchanged, and so are the schemas the frontend's types are
generated from.
"""
from __future__ import annotations

from pydantic import BaseModel


class LightMap(BaseModel):
    """Mean daily sun hours per cell, row-major from the south-west corner.

    `stale` is the honest half. The map is expensive enough to store, so it can
    be out of date — and a map that is quietly out of date is worse than one
    that says so. It is computed by comparing a signature of the shading inputs,
    not by remembering which actions ought to have invalidated it.
    """

    cell_m: float
    min_x: float
    min_y: float
    cols: int
    rows: int
    #: Null only where nothing can be answered: a building whose height nobody
    #: has recorded. A cell under a house is answered **on the roof** — at its
    #: own height and its own pitch, which at 51°N makes a north face and a
    #: south face very different places.
    hours: list[float | None]
    #: Which of those cells are a roof rather than ground, in step with `hours`.
    #: Empty on a grid computed before roofs were.
    roof: list[bool]
    #: The most any cell of **ground** gets, so the drawing can scale without a
    #: second pass. Roofs are left out of it: nothing is planted on one, and a
    #: sunny roof would otherwise set the scale for the garden below it.
    max_hours: float
    computed_at: str
    stale: bool
    #: The light model that computed it (`solar.light.MODEL_VERSION`); empty
    #: for a map computed before Wave 26 gave models a version.
    model: str = ""
    #: Of those hours, the ones before the sun crosses due south. Empty on a
    #: grid computed before the split existed; the next rebuild fills it, and
    #: nulls line up with `hours`.
    morning: list[float | None]
    #: Plantings standing in light they did not ask for.
    misplaced: list[MisplacedOut]


class MisplacedOut(BaseModel):
    """A planting standing in light it did not ask for.

    A warning, never a refusal: a gardener may know something the model does
    not — a cultivar bred for shade, a wall that throws light back, or simply
    that they want it there.
    """

    planting_id: int
    bed_id: int
    taxon_id: int
    name: str
    wants: float
    gets: float
    sun_hours: float
    #: 'too_dark' | 'too_bright'. Both happen; the second is the forgotten one.
    problem: str


class TerrainOut(BaseModel):
    """The ground under a garden, and how far it is to be trusted.

    Every field after `relief` is there so the page can answer "says who, and
    how good is it" without the reader having to know what a DGM1 is. A height
    shown without its credit is a height used outside its licence, and a height
    shown without its accuracy invites more confidence than it earns.
    """

    cell_m: float
    min_x: float
    min_y: float
    cols: int
    rows: int
    #: Relief shading, 0 (in shadow) to 1 (lit), row-major from the south-west.
    #: Sent already computed: it is one pass over the grid on a server that has
    #: the heights anyway, against shipping 40,000 metre values to a browser
    #: that would then do the same arithmetic.
    relief: list[float]
    #: Metres, lowest and highest, so the page can say what it is drawing.
    lowest: float
    highest: float
    source: str
    licence: str
    attribution: str
    #: 0.01 m for a DGM1. 1.0 for Baden-Württemberg's INSPIRE coverage, which
    #: cannot see a 20 m garden's own fall at all.
    vertical_step_m: float


class CreditOut(BaseModel):
    """One source a garden's numbers rest on (doc 106).

    A credit is not a caption: CC-BY-4.0, dl-de/by-2-0 and the Copernicus terms
    all require the named credit, and a height shown without it is a height
    used outside its licence.
    """

    #: `ground`, `horizon`, `buildings` — or several, where one survey gave
    #: more than one of them.
    about: str
    name: str
    licence: str
    attribution: str
    #: How fine it is, in the source's own terms. Null where it does not say.
    detail: str | None = None


class ShadowFrame(BaseModel):
    """Every shadow in the garden at one moment of one day."""

    #: Minutes since 00:00 UTC on the frame's day (the 15th of the month;
    #: `solar/day.py`). The page shows them on a Europe/Berlin clock.
    minute: int
    altitude: float
    azimuth: float
    #: Every shadow at this moment as rings — outlines anticlockwise, holes
    #: clockwise — drawn as one path under the non-zero rule (doc 116).
    polygons: list[list[list[float]]]


class ShadowDay(BaseModel):
    month: int
    day: int
    frames: list[ShadowFrame]
