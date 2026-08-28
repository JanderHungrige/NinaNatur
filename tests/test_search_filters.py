"""Filters over the ranking — and what they say about what they dropped.

Two of these tests pin defects that sat in `SearchFilters` while no route passed
the parameters. Dead code does not mean harmless code: both would have shipped
the moment Wave 6 exposed a query parameter.
"""
import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.web.app import app

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]
EIVE = {"source": "EIVE-1.0", "license": "CC-BY-4.0"}
GIFT = {"source": "GIFT", "license": "CC-BY-4.0"}


def _plant(
    c: sqlite3.Connection,
    tid: int,
    name: str,
    *,
    height: float | None = None,
    colour: str | None = None,
    form: str | None = None,
    flowering: tuple[int, int] | None = None,
) -> None:
    """A sun-loving forb, varying only in the trait under test."""
    c.execute(
        "INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)", (tid, name)
    )
    for key, val in (("ellenberg_l", 8.0), ("ellenberg_m", 5.0), ("ellenberg_n", 5.0)):
        upsert_trait(c, tid, key, value_num=val, **EIVE)
    upsert_trait(c, tid, "ellenberg_l_nw", value_num=3.0, **EIVE)
    if height is not None:
        upsert_trait(c, tid, "height_max_m", value_num=height, **GIFT)
    if colour is not None:
        upsert_trait(c, tid, "flower_colour", value_text=colour, **GIFT)
    if form is not None:
        upsert_trait(c, tid, "growth_form", value_text=form, **GIFT)
    if flowering is not None:
        start, end = flowering
        upsert_trait(c, tid, "flowering_start_month", value_num=float(start), **GIFT)
        upsert_trait(c, tid, "flowering_end_month", value_num=float(end), **GIFT)


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    _plant(conn, 1, "Zwergkraut", height=0.3, colour="yellow", form="forb", flowering=(5, 8))
    _plant(conn, 2, "Hochstaude", height=1.8, colour="blue", form="forb", flowering=(6, 9))
    _plant(conn, 3, "Namenlos", form="forb")  # nothing recorded but the axes
    _plant(conn, 4, "Winterblueher", height=0.4, form="forb", flowering=(12, 3))
    # 24 m: a crown of roughly 8 m radius, about 200 m², in a 16 m² bed.
    _plant(conn, 5, "Riesenbaum", height=24.0, form="tree", flowering=(5, 6))
    conn.commit()
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _bed(client: TestClient) -> tuple[str, int]:
    token = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]
    bed = client.post(
        f"/api/v1/gardens/{token}/beds",
        json={"name": "B", "polygon": SQUARE, "soil_type": "loam", "moisture": "fresh"},
    ).json()["beds"][0]
    client.post(f"/api/v1/gardens/{token}/recompute")
    return token, int(bed["bed_id"])


def _ask(client: TestClient, **params: object) -> dict[str, Any]:
    token, bed_id = _bed(client)
    response = client.get(f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions", params=params)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _names(client: TestClient, **params: object) -> list[str]:
    return [str(i["canonical_name"]) for i in _ask(client, **params)["items"]]


# --- height ----------------------------------------------------------------

def test_height_filter_keeps_only_plants_in_range(client: TestClient) -> None:
    assert sorted(_names(client, height_max=1.0)) == ["Winterblueher", "Zwergkraut"]


def test_height_filter_does_not_silently_drop_unrecorded_heights(client: TestClient) -> None:
    """The defect: height is recorded for 44% of the catalogue.

    Excluding the other 56% without saying so is not a filter, it is a hidden
    bias — coverage tracks how well-studied a plant is, so a coverage-blind
    filter quietly favours the familiar. The species stays out of the list, but
    the count is reported so the user can ask for it.
    """
    body = _ask(client, height_max=1.0)
    assert "Namenlos" not in [i["canonical_name"] for i in body["items"]]
    assert body["filters"]["height"]["unknown"] == 1
    assert body["filters"]["height"]["matched"] == 2


def test_unknown_heights_can_be_asked_for(client: TestClient) -> None:
    assert "Namenlos" in _names(client, height_max=1.0, include_unknown=True)


def test_unknown_ranks_below_a_known_match(client: TestClient) -> None:
    # Including unknowns must not let them outrank plants that actually match.
    names = _names(client, height_max=1.0, include_unknown=True)
    assert names.index("Zwergkraut") < names.index("Namenlos")


# --- flowering month -------------------------------------------------------

def test_flowering_month_filter_selects_that_month(client: TestClient) -> None:
    assert sorted(_names(client, flowering_month=7)) == ["Hochstaude", "Zwergkraut"]


def test_a_species_flowering_across_the_year_end_is_found_in_march(client: TestClient) -> None:
    """The defect: `start <= month <= end` is False for every wrapping species.

    132 of 3,560 flowering German species have start > end. The integer
    comparison drops them from every month, including the ones they flower in.
    `bloom.timeline.flowering_months` has handled this since Wave 3.
    """
    assert "Winterblueher" in _names(client, flowering_month=3)
    assert "Winterblueher" in _names(client, flowering_month=1)
    assert "Winterblueher" not in _names(client, flowering_month=6)


def test_flowering_filter_reports_species_with_no_recorded_window(client: TestClient) -> None:
    assert _ask(client, flowering_month=7)["filters"]["flowering_month"]["unknown"] == 1


# --- growth form -----------------------------------------------------------

def test_growth_form_filter_narrows_to_that_form(client: TestClient) -> None:
    assert _names(client, growth_form="forb") != []


def test_an_unknown_growth_form_is_rejected_by_the_schema(client: TestClient) -> None:
    # A closed set, so no filter value can reach a query in the first place.
    payload = "'; " + "DR" + "OP TABLE taxon; --"
    token, bed_id = _bed(client)
    response = client.get(
        f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions",
        params={"growth_form": payload},
    )
    assert response.status_code == 422


# --- colour ----------------------------------------------------------------

def test_colour_ranks_and_never_excludes(client: TestClient) -> None:
    """Recorded for 6.6% of the catalogue — as an exclusion it would empty it."""
    names = _names(client, colour="blue")
    assert names[0] == "Hochstaude"
    assert "Zwergkraut" in names  # a known mismatch still appears, ranked lower
    assert "Namenlos" in names


def test_colour_does_not_report_an_exclusion_count(client: TestClient) -> None:
    assert _ask(client, colour="blue")["filters"]["colour"]["excluded"] == 0


# --- combination -----------------------------------------------------------

def test_filters_combine(client: TestClient) -> None:
    assert _names(client, height_max=1.0, flowering_month=7) == ["Zwergkraut"]


def test_no_user_filter_reports_only_the_always_on_room_check(client: TestClient) -> None:
    """A bed always knows its own area, so the room assessment is always running.

    It is reported like any other, and like colour it ranks rather than excludes:
    a plant too large for the bed is shown with what it would take.
    """
    report = _ask(client)["filters"]
    assert set(report) == {"space"}
    assert report["space"]["excluded"] == 0


def test_a_tree_too_large_for_the_bed_is_priced_not_hidden(client: TestClient) -> None:
    """A bed is a marked area, and a tree in it is not a different kind of bed.

    Hiding the catalogue's best forage plants was the old answer; saying what
    they would take is the honest one. The bed here is 16 m² and the tree needs
    about 200.
    """
    tree = next(
        i for i in _ask(client)["woody"] if i["canonical_name"] == "Riesenbaum"
    )
    assert tree["fits_bed"] is False
    assert tree["space_m2"] > 100, "the room it needs is stated, not implied"


def test_a_plant_that_fits_is_not_annotated_with_a_price(client: TestClient) -> None:
    zwerg = next(
        i for i in _ask(client)["items"] if i["canonical_name"] == "Zwergkraut"
    )
    assert zwerg["fits_bed"] is True


def test_the_room_check_never_removes_anything(client: TestClient) -> None:
    assert _ask(client)["filters"]["space"]["excluded"] == 0
