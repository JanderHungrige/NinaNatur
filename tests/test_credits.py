"""Which source said so — Wave 25, feature 7 (doc 106).

A garden may rest on three surveys now, each with a licence that asks for
something. These are about the list a page shows: that it names what was
actually used, that it never prints a credit for a source the garden did not
touch, and that a state which gave two things is thanked once for both.
"""
from __future__ import annotations

from ninanatur.garden.credits import credits_for, tiles_available
from ninanatur.garden.models import Element, Garden
from ninanatur.geo.terrain import TerrainWindow


def _garden(height_source: str = "assumed") -> Garden:
    house = Element(
        element_id=1, kind="house", shape="polygon", x=0.0, y=0.0,
        points=[[-4.5, -3.0], [4.5, -3.0], [4.5, 3.0], [-4.5, 3.0]],
        height=9.0, height_source=height_source, roof="gable", eaves_m=6.0,
    )
    return Garden(
        garden_id=1, share_token="t", owner_id=None, name="G",
        latitude=48.137, longitude=11.575, created_at="", updated_at="",
        elements=[house],
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
    [ground_only] = credits_for(_garden(height_source="assumed"), ground=_ground(),
                                horizon_source=None)
    assert ground_only.about == "ground"
    both = credits_for(_garden(height_source="survey"), ground=_ground(),
                       horizon_source=None)
    assert [c.about for c in both] == ["ground, buildings"]


def test_every_state_with_a_building_model_also_publishes_its_ground() -> None:
    """The invariant the credit above rests on. The building model is named from
    the ground window's state, because looking it up would be a reverse geocode
    on a page load — and that holds only while no state publishes LoD2 and no
    ground. If this ever fails, the state it names needs `measured_by` on the
    element instead (doc 106)."""
    from ninanatur.geo.terrain_sources import by_state as service
    from ninanatur.geo.tile_sources import (
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
    found = credits_for(_garden(height_source="survey"), ground=_ground(),
                        horizon_source=None)
    assert len(found) == 1
    assert found[0].about == "ground, buildings"


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
