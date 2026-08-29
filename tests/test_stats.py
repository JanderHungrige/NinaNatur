"""The figures the landing page states, and where they come from.

A page that states a species count is making a claim. Wave 1 wrote "3.087" into
its HTML by hand, and it was wrong the first time the catalogue was rebuilt.
"""
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.data.sources import SOURCES
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.web.app import app

AXES = ("ellenberg_l", "ellenberg_m", "ellenberg_n", "ellenberg_r")


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    for tid, complete in ((1, True), (2, True), (3, False)):
        conn.execute(
            "INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
            (tid, f"Art {tid}"),
        )
        for axis in AXES if complete else AXES[:2]:
            upsert_trait(conn, tid, axis, value_num=5.0, source="EIVE-1.0",
                         license="CC-BY-4.0")
    conn.execute("INSERT INTO partner_totals (taxon_id, german, global_total, unmatched)"
                 " VALUES (1, 40, 60, 20)")
    conn.execute("INSERT INTO partner_totals (taxon_id, german, global_total, unmatched)"
                 " VALUES (2, 12, 30, 18)")
    conn.execute("INSERT INTO insect_de (canonical_name, occurrences) VALUES ('Apis mellifera', 9)")
    conn.commit()
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_the_figures_come_from_the_data(client: TestClient) -> None:
    body = client.get("/api/v1/stats").json()
    assert body["species"] == 3
    assert body["species_with_full_site_profile"] == 2
    assert body["animal_partnerships"] == 52
    assert body["german_animals"] == 1


def test_it_names_its_sources_with_their_licences(client: TestClient) -> None:
    """A licence claim on a landing page is the licence position in public."""
    body = client.get("/api/v1/stats").json()
    names = {s["name"] for s in body["sources"]}
    assert names == {s.name for s in SOURCES}
    for source in body["sources"]:
        assert source["licence"]
        assert source["url"].startswith("https://")


def test_every_ingest_adapter_is_declared_as_a_source() -> None:
    """A new adapter that nobody adds here makes the page understate its own
    provenance — which is the one thing this project cannot be sloppy about."""
    from ninanatur.ingest.sources import eive, gbif, gift, globi

    declared = " ".join(s.name.lower() for s in SOURCES)
    for module in (eive, gbif, gift, globi):
        stem = module.__name__.rsplit(".", 1)[-1]
        assert stem in declared.replace(" ", "").replace("1.0", ""), stem


def test_an_empty_catalogue_reports_zero_rather_than_failing(client: TestClient) -> None:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    body = client.get("/api/v1/stats").json()
    assert body["species"] == 0
    assert body["animal_partnerships"] == 0


def test_the_figures_are_not_hardcoded(client: TestClient) -> None:
    """Wave 1's page said 3.087 species because someone typed it."""
    conn = app.dependency_overrides[get_connection]()
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (99, 'Neu', 1)")
    conn.commit()
    assert client.get("/api/v1/stats").json()["species"] == 4
