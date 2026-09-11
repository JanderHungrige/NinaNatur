"""What the measurement pass looks at, and what it costs — Wave 20, feature 10.

Found on the preview on 2026-09-11 while checking feature 8: `POST /light` on a
real Wuppertal garden took five to seven minutes, in the request thread. The
parsers took a second; `measured.py` took the rest. Every half-metre sample of
every building drawn on the plan was tested against every one of the tile's
2,601 surveyed buildings, with no box around them first. On a second dense
garden, measured on a laptop against the same real tile: 19.13 s, three houses
matched. With a box first: 0.04 s, the same three houses at the same heights.

And the pass measured whatever carried a height that nobody had typed — which
includes a tree found by the canopy pass and accepted, stored as `measured`.
Matched against the survey, a tree over a house takes the house's roof.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from dataclasses import replace

import pytest

from ninanatur.garden import measured
from ninanatur.garden.elements import insert_element
from ninanatur.garden.measured import MATCH_OVERLAP, measure
from ninanatur.garden.models import Garden
from ninanatur.garden.roofs import Roof
from ninanatur.garden.store import create_garden, load_garden
from ninanatur.geo.lod2 import Lod2Building
from ninanatur.geo.surface import SurfaceWindow
from ninanatur.ingest.db import connect, init_schema

Points = list[list[float]]


def _square(cx: float, cy: float, half: float) -> Points:
    return [[cx - half, cy - half], [cx + half, cy - half],
            [cx + half, cy + half], [cx - half, cy + half]]


HOUSE: Points = [[-4.0, -10.0], [4.0, -10.0], [4.0, -4.0], [-4.0, -4.0]]
#: One of each thing a garden holds, standing or lying down.
DRAWN: dict[str, Points] = {
    "house": HOUSE,
    # Six metres square: the raster erodes a footprint by two metres before it
    # samples it (`geo/measure.py`), and a garden shed would keep nothing.
    "shed": _square(12.0, 12.0, 3.0),
    "hedge": [[-15.0, 14.0], [-5.0, 14.0], [-5.0, 14.6], [-15.0, 14.6]],
    "tree": _square(15.0, -15.0, 3.0),
    "garden": _square(0.0, 0.0, 25.0),
    "lawn": _square(-12.0, 0.0, 4.0),
    "street": [[-40.0, 28.0], [40.0, 28.0], [40.0, 34.0], [-40.0, 34.0]],
}
FLAT = ("garden", "lawn", "street")


@pytest.fixture()
def garden() -> Iterator[Garden]:
    conn: sqlite3.Connection = connect(":memory:")
    init_schema(conn)
    garden_id = create_garden(conn, name="G", latitude=51.0, longitude=6.0)
    for kind, points in DRAWN.items():
        # Nothing here was typed by a person, so nothing is protected by that:
        # what is left out is left out for what it is.
        insert_element(conn, garden_id, kind=kind, shape="polygon", x=0.0, y=0.0,
                       points=points, height=None if kind in FLAT else 3.0,
                       height_source="measured" if kind == "tree" else "osm_levels")
    conn.commit()
    yield load_garden(conn, garden_id)
    conn.close()


def _ids(garden: Garden, *kinds: str) -> set[int]:
    return {o.obstacle_id for o in garden.obstacles if o.kind in kinds}


def _uniform(height: float) -> SurfaceWindow:
    """A hundred metres square at half a metre, centred on the garden."""
    size = 200
    return SurfaceWindow(min_x=-50.0, min_y=-50.0, cell_m=0.5, cols=size, rows=size,
                         heights=[height] * (size * size),
                         source="Test", licence="—", attribution="—")


def _tile(match_height: float) -> list[Lod2Building]:
    """2,601 buildings on a twenty-metre grid over a square kilometre — the
    density of the Wuppertal tile — one of them exactly where the house is drawn."""
    tile = []
    for i in range(51):
        for j in range(51):
            x, y = -500.0 + 20.0 * i, -507.0 + 20.0 * j
            tile.append(Lod2Building(
                building_id=f"DE_{i}_{j}", roof=Roof.GABLE, eaves_m=None,
                height_m=match_height if (i, j) == (25, 25) else 30.0,
                outline=[(x - 4, y - 3), (x + 4, y - 3), (x + 4, y + 3), (x - 4, y + 3)],
            ))
    return tile


# --- only buildings are measured ---------------------------------------------------------

def test_only_houses_and_sheds_are_measured(garden: Garden) -> None:
    """The laser surface gave a hedge, an accepted tree, the lawn, the street
    and the garden itself a "measured" height, as though each were a roof."""
    found = measure(garden, surface=_uniform(8.0))

    assert {m.obstacle_id for m in found} == _ids(garden, "house", "shed")


def test_an_accepted_tree_does_not_take_the_roof_it_stands_over(garden: Garden) -> None:
    """Stored as `measured`, so no person's word protects it — only its kind."""
    over_the_tree = Lod2Building(
        building_id="DE_UNDER", roof=Roof.HIP, height_m=11.0, eaves_m=7.5,
        outline=[(11.0, -19.0), (19.0, -19.0), (19.0, -11.0), (11.0, -11.0)],
    )
    found = measure(garden, surveyed=[over_the_tree])

    assert _ids(garden, "tree").isdisjoint({m.obstacle_id for m in found})


def test_the_ground_is_never_matched_against_the_survey(garden: Garden) -> None:
    """Not even under a surveyed building that covers all of it."""
    covering = Lod2Building(
        building_id="DE_HALL", roof=Roof.FLAT, height_m=20.0, eaves_m=None,
        outline=[(-60.0, -60.0), (60.0, -60.0), (60.0, 60.0), (-60.0, 60.0)],
    )
    found = measure(garden, surveyed=[covering])

    assert {m.obstacle_id for m in found} == _ids(garden, "house", "shed")


# --- a box before a polygon --------------------------------------------------------------

def test_a_house_in_a_dense_tile_is_matched_box_first(
    garden: Garden, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The cost was samples x buildings x corners. A box around each building,
    computed once, leaves the handful that can overlap."""
    calls: list[int] = []
    real: Callable[[list[tuple[float, float]], float, float], bool] = measured._inside

    def counted(polygon: list[tuple[float, float]], x: float, y: float) -> bool:
        calls.append(1)
        return real(polygon, x, y)

    monkeypatch.setattr(measured, "_inside", counted)
    only_house = replace(garden, elements=[e for e in garden.elements if e.kind == "house"])

    [found] = measure(only_house, surveyed=_tile(12.4))

    assert found.height_m == pytest.approx(12.4)
    assert len(calls) < 5_000, f"{len(calls)} polygon tests for one house"


def test_the_box_drops_nothing_that_could_have_matched(garden: Garden) -> None:
    """A sample inside the drawn outline can only be inside a surveyed one whose
    box holds it. Checked against the whole tile, one building at a time."""
    tile = _tile(12.4) + [Lod2Building(
        building_id="DE_SHED", roof=Roof.PENT, height_m=4.2, eaves_m=None,
        outline=[(11.0, 11.0), (15.0, 11.0), (15.0, 15.0), (11.0, 15.0)],
    )]
    found = {m.obstacle_id: m.height_m for m in measure(garden, surveyed=tile)}

    for obstacle in garden.obstacles:
        if obstacle.kind not in ("house", "shed"):
            continue
        points = measured._sample([(float(x), float(y)) for x, y in obstacle.footprint])
        best = max(tile, key=lambda b: measured._covered(points, b.outline))
        matched = measured._covered(points, best.outline) > MATCH_OVERLAP
        assert found.get(obstacle.obstacle_id) == (round(best.height_m, 1) if matched else None)
    assert set(found) == _ids(garden, "house", "shed")
