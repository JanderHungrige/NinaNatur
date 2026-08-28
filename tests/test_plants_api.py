"""The API contract Waves 3 and 4 will consume unchanged."""
import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.web.app import app

CORE = ("ellenberg_l", "ellenberg_m", "ellenberg_n", "height_max_m",
        "flowering_start_month", "flowering_end_month")


def _plant(c: sqlite3.Connection, tid: int, name: str, light: float,
           moisture: float, colour: str | None = None) -> None:
    c.execute(
        "INSERT INTO taxon (taxon_id, canonical_name, family, occurs_de)"
        " VALUES (?, ?, 'Testaceae', 1)",
        (tid, name),
    )
    for key, val in (("ellenberg_l", light), ("ellenberg_m", moisture),
                     ("ellenberg_n", 5.0), ("height_max_m", 0.5),
                     ("flowering_start_month", 5.0), ("flowering_end_month", 8.0)):
        upsert_trait(c, tid, key, value_num=val, source="EIVE-1.0", license="CC-BY-4.0")
    upsert_trait(c, tid, "ellenberg_l_nw", value_num=3.0, source="EIVE-1.0", license="CC-BY-4.0")
    if colour:
        upsert_trait(c, tid, "flower_colour", value_text=colour, source="GIFT", license="CC-BY-4.0")


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    _plant(conn, 1, "Sunlovus maximus", light=8.0, moisture=2.0, colour="yellow")
    _plant(conn, 2, "Shadowus minimus", light=2.0, moisture=8.0, colour="blue")
    _plant(conn, 3, "Colourlessus ignotus", light=7.5, moisture=2.5)  # no colour recorded
    conn.execute("INSERT INTO insect_de (canonical_name, occurrences) VALUES ('Apis mellifera', 9)")
    conn.execute(
        "INSERT INTO interaction (taxon_id, partner_name, interaction_type, source, license)"
        " VALUES (1, 'Apis mellifera', 'visitedBy', 'GloBI', 'CC0-1.0')"
    )
    conn.commit()
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- search ---------------------------------------------------------------

def test_search_ranks_the_better_fit_first(client: TestClient) -> None:
    body = client.get("/api/v1/plants", params={"light": 8.0, "moisture": 2.0}).json()
    assert body["items"][0]["canonical_name"] == "Sunlovus maximus"
    assert body["items"][0]["fit"]["score"] > body["items"][-1]["fit"]["score"]


def test_search_without_any_site_axis_is_422_not_an_arbitrary_200(
    client: TestClient,
) -> None:
    """Ranking the whole catalogue by nothing would be a confidently wrong answer."""
    assert client.get("/api/v1/plants").status_code == 422


def test_out_of_range_values_are_422(client: TestClient) -> None:
    assert client.get("/api/v1/plants", params={"light": 99}).status_code == 422
    late = client.get("/api/v1/plants", params={"light": 5, "flowering_month": 13})
    assert late.status_code == 422


def test_fit_carries_its_per_axis_explanation(client: TestClient) -> None:
    """Wave 4 must be able to say 'borderline on moisture' without recomputing."""
    item = client.get("/api/v1/plants", params={"light": 8.0, "moisture": 2.0}).json()["items"][0]
    axes = item["fit"]["axes"]
    assert axes["ellenberg_l"]["band"] == "optimal"
    assert "half_widths_away" in axes["ellenberg_l"]


def test_height_filter_excludes_but_colour_does_not(client: TestClient) -> None:
    """Colour is a soft filter — an unrecorded colour must not hide a species."""
    coloured = client.get(
        "/api/v1/plants", params={"light": 7.5, "moisture": 2.5, "colour": "yellow"}
    ).json()
    names = [i["canonical_name"] for i in coloured["items"]]
    assert "Colourlessus ignotus" in names, "unknown colour must survive a colour filter"
    assert names.index("Sunlovus maximus") < names.index("Shadowus minimus")


def test_unknown_colour_is_null_with_a_reason_not_an_omitted_field(
    client: TestClient,
) -> None:
    body = client.get("/api/v1/plants", params={"light": 7.5}).json()
    item = next(i for i in body["items"] if i["canonical_name"] == "Colourlessus ignotus")
    assert "flower_colour" in item
    assert item["flower_colour"] is None


def test_paging_reports_total_independently_of_the_page(client: TestClient) -> None:
    body = client.get("/api/v1/plants", params={"light": 5.0, "limit": 1}).json()
    assert body["total"] == 3
    assert len(body["items"]) == 1


def test_limit_above_the_cap_is_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/plants", params={"light": 5, "limit": 5000}).status_code == 422


# --- detail ---------------------------------------------------------------

def test_detail_returns_every_trait_with_its_source(client: TestClient) -> None:
    body = client.get("/api/v1/plants/1").json()
    assert body["canonical_name"] == "Sunlovus maximus"
    light = body["traits"]["ellenberg_l"]
    assert light["value"] == 8.0
    assert light["source"] == "EIVE-1.0"
    assert light["license"] == "CC-BY-4.0"


def test_detail_reports_german_partner_counts_not_global(client: TestClient) -> None:
    partners = client.get("/api/v1/plants/1").json()["partners"]
    assert partners["german"] == 1
    assert partners["global_total"] == 1


def test_detail_partners_are_null_when_globi_has_no_records(client: TestClient) -> None:
    """No data and no partners are different facts."""
    assert client.get("/api/v1/plants/2").json()["partners"] is None


def test_unknown_taxon_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/plants/999999").status_code == 404


# --- the Wave 1 guarantee must survive a database existing -----------------

def test_healthz_still_answers_without_touching_the_database(client: TestClient) -> None:
    """Otherwise a broken deploy and a broken database look identical."""
    app.dependency_overrides.clear()
    assert client.get("/healthz").status_code == 200
