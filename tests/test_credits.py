"""Which source said so — Wave 25, feature 7 (doc 106).

A garden may rest on three surveys now, each with a licence that asks for
something. These are about the list a page shows: that it names what was
actually used, that it never prints a credit for a source the garden did not
touch, and that a state which gave two things is thanked once for both.
"""
from __future__ import annotations

import pytest

from ninanatur.garden.credits import credits_for, from_the_map, tiles_available
from ninanatur.garden.models import Element, Garden
from ninanatur.geo.terrain import TerrainWindow


def _garden(height_source: str = "user", *extra: Element,
            outline_source: str | None = None) -> Garden:
    """One house — drawn by hand unless the map import brought its outline."""
    house = Element(
        element_id=1, kind="house", shape="polygon", x=0.0, y=0.0,
        points=[[-4.5, -3.0], [4.5, -3.0], [4.5, 3.0], [-4.5, 3.0]],
        height=9.0, height_source=height_source, roof="gable", eaves_m=6.0,
        outline_source=outline_source,
    )
    return Garden(
        garden_id=1, share_token="t", owner_id=None, name="G",
        latitude=48.137, longitude=11.575, created_at="", updated_at="",
        elements=[house, *extra],
    )


def _ground(source: str = "BY", licence: str = "CC-BY-4.0") -> TerrainWindow:
    return TerrainWindow(
        min_x=-100.0, min_y=-100.0, cell_m=1.0, cols=10, rows=10, heights=[520.0] * 100,
        source=source, licence=licence,
        attribution="Datenquelle: Bayerische Vermessungsverwaltung – www.geodaten.bayern.de",
        vertical_step_m=0.01,
    )


def test_a_garden_with_nothing_measured_owes_nobody_anything() -> None:
    assert credits_for(_garden(), ground=None, horizon_source=None) == []


def test_the_ground_is_credited_from_the_window_it_came_with() -> None:
    [credit] = credits_for(_garden(), ground=_ground(), horizon_source=None)
    assert credit.about == "ground"
    assert credit.licence == "CC-BY-4.0"
    assert "Bayerische Vermessungsverwaltung" in credit.attribution
    assert credit.detail == "1 m, ±0.01 m"


def test_a_copernicus_ring_carries_the_credit_its_terms_ask_for() -> None:
    """Feature 2 gave nine states a horizon and, with it, an obligation: the
    Copernicus terms name DLR, Airbus and ESA (doc 104)."""
    found = credits_for(_garden(), ground=None, horizon_source="Copernicus GLO-30")
    [ring] = found
    assert ring.about == "horizon"
    assert ring.detail == "30 m"
    for who in ("DLR", "Airbus", "ESA"):
        assert who in ring.attribution, who


def test_the_building_model_is_credited_only_where_it_measured_something() -> None:
    """A state publishing LoD2 is not a credit. A house in this garden carrying
    a surveyed height is. Which state is read off the ground window, which is
    what the garden was measured against."""
    [ground_only] = credits_for(_garden(height_source="user"), ground=_ground(),
                                horizon_source=None)
    assert ground_only.about == "ground"
    # A surveyed house came from the map: its outline is still OpenStreetMap's.
    both = credits_for(_garden("surveyed", outline_source="osm"), ground=_ground(),
                       horizon_source=None)
    assert [c.about for c in both] == ["ground, buildings", "map"]


def test_the_building_credit_answers_to_what_the_survey_writes() -> None:
    """It compared against "survey", which nothing writes, and these tests used
    the same word — so the building model was credited here and never on a page."""
    from ninanatur.geo.surroundings import HeightSource

    found = credits_for(_garden(height_source=HeightSource.SURVEYED.value), ground=_ground(),
                        horizon_source=None)
    assert "buildings" in found[0].about


def test_every_state_with_a_building_model_also_publishes_its_ground() -> None:
    """The invariant the credit above rests on. The building model is named from
    the ground window's state, because looking it up would be a reverse geocode
    on a page load — and that holds only while no state publishes LoD2 and no
    ground. If this ever fails, the state it names needs `measured_by` on the
    element instead (doc 106)."""
    from geokachel.terrain_sources import by_state as service
    from geokachel.tile_sources import (
        TILE_SOURCES,
        TileProduct,
        ground_tiles_for,
        name_of,
    )

    for source in TILE_SOURCES:
        if source.product is not TileProduct.LOD2:
            continue
        has_ground = (ground_tiles_for(source.state) is not None
                      or service(name_of(source.state)) is not None)
        assert has_ground, (
            f"{source.state} publishes LoD2 and no ground: the credit cannot name it")


def test_a_state_that_gave_two_things_is_thanked_once_for_both() -> None:
    """Bayern's ground and its roofs are one licence and one attribution. Two
    identical paragraphs under a plan is not more correct, only longer."""
    found = credits_for(_garden("surveyed", outline_source="osm"), ground=_ground(),
                        horizon_source=None)
    assert [c.about for c in found] == ["ground, buildings", "map"]


def test_two_different_sources_are_two_credits() -> None:
    found = credits_for(_garden(), ground=_ground(), horizon_source="Copernicus GLO-30")
    assert [c.about for c in found] == ["ground", "horizon"]
    assert len({c.licence for c in found}) == 2


def test_a_state_with_tiles_is_known_to_have_them() -> None:
    """What doc 103 added, and what a garden computed before it does not know."""
    assert tiles_available("Bayern") is True
    assert tiles_available("Hessen") is False
    assert tiles_available(None) is False


def test_the_page_can_ask_a_garden_what_it_rests_on() -> None:
    """A garden nobody has measured anything for owes nobody anything, and an
    empty list is the honest answer rather than a 404."""
    import sqlite3

    from fastapi.testclient import TestClient

    from ninanatur.api.deps import get_connection
    from ninanatur.ingest.db import connect, init_schema
    from ninanatur.web.app import app

    conn: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    try:
        client = TestClient(app)
        token = client.post("/api/v1/gardens",
                            json={"name": "G", "latitude": 48.137, "longitude": 11.575}
                            ).json()["share_token"]
        answer = client.get(f"/api/v1/gardens/{token}/sources")
        assert answer.status_code == 200
        assert answer.json() == []
    finally:
        app.dependency_overrides.clear()


def test_the_laser_is_credited_where_one_was_read() -> None:
    """Feature 4's source (doc 107). NRW's cloud is dl-de/zero-2-0, which asks
    for nothing and is credited anyway — the page says where a crown base came
    from, and a number whose origin is not shown is a number nobody can check."""
    [laser] = credits_for(_garden(), ground=None, horizon_source=None, laser_source="NW")
    assert laser.about == "laser"
    assert laser.name == "Laserscan Nordrhein-Westfalen"
    assert laser.licence == "dl-de/zero-2-0"
    assert "NRW" in laser.attribution
    assert laser.detail == "4 Punkte/m²"


def test_a_state_with_no_open_cloud_is_credited_for_nothing() -> None:
    assert credits_for(_garden(), ground=None, horizon_source=None,
                       laser_source="Hessen") == []


# OpenStreetMap (owner's check, 2026-09-21, #10): a garden made from the map
# draws OSM's streets and house outlines, and ODbL asks for the credit wherever
# they are shown. Nothing records where an outline came from; the import leaves
# its mark on the provenance columns, and those are what is read.

def _street() -> Element:
    return Element(element_id=2, kind="street", shape="line", x=0.0, y=-12.0,
                   points=[[-20.0, 0.0], [20.0, 0.0]], width=6.0, label="Hauptstraße")


def test_openstreetmap_is_credited_where_its_streets_are_drawn() -> None:
    [osm] = credits_for(_garden("user", _street()), ground=None, horizon_source=None)
    assert osm.about == "map"
    assert osm.name == "OpenStreetMap"
    assert osm.licence == "ODbL-1.0"
    assert osm.attribution == "© OpenStreetMap-Mitwirkende"


@pytest.mark.parametrize("height_source", [
    "osm_height", "osm_levels", "neighbourhood",
    # A survey or the laser replaces the height and the roof, never the outline.
    "surveyed", "measured",
    # Nor does the gardener typing a height: the outline is still OpenStreetMap's.
    "user",
])
def test_a_house_from_the_map_is_credited_whatever_later_measured_it(height_source: str) -> None:
    found = credits_for(_garden(height_source, outline_source="osm"), ground=None,
                        horizon_source=None)
    assert [c.about for c in found] == ["map"]


def test_a_map_house_whose_height_and_roof_were_both_corrected_keeps_its_credit() -> None:
    """The inferred rule lost it: nothing but the outline was OpenStreetMap's
    any more, and the outline was what the plan still drew (review, 2026-09-21)."""
    corrected = Element(element_id=3, kind="house", shape="polygon", x=0.0, y=0.0,
                        points=[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0]], height=7.0,
                        height_source="user", roof="gable", roof_source="user",
                        outline_source="osm")
    assert from_the_map(corrected)


def test_a_house_drawn_by_hand_is_not_the_maps_whatever_its_height_says() -> None:
    surveyed = Element(element_id=4, kind="house", shape="polygon", x=0.0, y=0.0,
                       points=[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0]], height=7.0,
                       height_source="surveyed", roof_source="surveyed")
    assert not from_the_map(surveyed)


def test_a_garden_drawn_by_hand_owes_openstreetmap_nothing() -> None:
    """A tree found in the laser and accepted is `measured` too, and no building."""
    tree = Element(element_id=5, kind="tree", shape="circle", x=3.0, y=3.0, width=6.0,
                   height=11.0, height_source="measured")
    lawn = Element(element_id=6, kind="lawn", shape="polygon", x=0.0, y=0.0,
                   points=[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0]])
    assert credits_for(_garden("user", tree, lawn), ground=None, horizon_source=None) == []


def test_the_page_is_told_about_openstreetmap_once_a_street_is_drawn() -> None:
    import sqlite3

    from fastapi.testclient import TestClient

    from ninanatur.api.deps import get_connection
    from ninanatur.ingest.db import connect, init_schema
    from ninanatur.web.app import app

    conn: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    try:
        client = TestClient(app)
        token = client.post("/api/v1/gardens",
                            json={"name": "G", "latitude": 48.137, "longitude": 11.575}
                            ).json()["share_token"]
        client.post(f"/api/v1/gardens/{token}/obstacles",
                    json={"kind": "house", "x": 0, "y": 0, "height": 8})
        assert client.get(f"/api/v1/gardens/{token}/sources").json() == []
        client.post(f"/api/v1/gardens/{token}/obstacles",
                    json={"kind": "street", "x": 0, "y": -12})
        [osm] = client.get(f"/api/v1/gardens/{token}/sources").json()
        assert osm["about"] == "map"
        assert osm["licence"] == "ODbL-1.0"
    finally:
        app.dependency_overrides.clear()
