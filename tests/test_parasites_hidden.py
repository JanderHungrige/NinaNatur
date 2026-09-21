"""Plants that live on a host or a fungus are no suggestion anywhere (owner, 2026-09-21).

"yes hide parasitic species like Lathraea from suggestions." Every species here
fits the bed perfectly and has insect partners, so the only thing that can keep
one out is what it lives on.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.api.parasites import is_parasitic
from ninanatur.bloom.improve import garden_improvements
from ninanatur.garden.store import load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.solar.light import SUN_HOUR_ANCHORS
from ninanatur.web.app import app

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]
EIVE = {"source": "EIVE-1.0", "license": "CC-BY-4.0"}
#: What an open bed on loam, fresh, gets: full sun and `site_axes_from_soil`.
SITE = {"ellenberg_l": SUN_HOUR_ANCHORS[-1][1], "ellenberg_m": 5.0,
        "ellenberg_n": 5.5, "ellenberg_r": 6.5}

HIDDEN = ("Lathraea squamaria", "Orobanche caryophyllacea", "Cuscuta europaea",
          "Neottia nidus-avis", "Viscum album")
KEPT = ("Rhinanthus minor", "Neottia ovata", "Melampyrum pratense")


def _species(c: sqlite3.Connection, tid: int, name: str, form: str) -> None:
    c.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
              (tid, name))
    for key, value in SITE.items():
        upsert_trait(c, tid, key, value_num=value, **EIVE)
        upsert_trait(c, tid, f"{key}_nw", value_num=3.0, **EIVE)
    upsert_trait(c, tid, "growth_form", value_text=form, source="GIFT", license="CC-BY-4.0")
    upsert_trait(c, tid, "native_de", value_text="native", source="GBIF-WCVP",
                 license="CC-BY-4.0")
    for key, month in (("flowering_start_month", 5.0), ("flowering_end_month", 7.0)):
        upsert_trait(c, tid, key, value_num=month, source="GIFT", license="CC-BY-4.0")
    c.execute("INSERT INTO partner_totals (taxon_id, german, global_total, unmatched)"
              " VALUES (?, 40, 40, 0)", (tid,))


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    c = connect(":memory:", same_thread=False)
    init_schema(c)
    for tid, name in enumerate(HIDDEN + KEPT, start=1):
        _species(c, tid, name, "shrub" if name.startswith("Viscum") else "forb")
    c.commit()
    yield c


@pytest.fixture()
def client(conn: sqlite3.Connection) -> Iterator[TestClient]:
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _bed(client: TestClient) -> tuple[str, int]:
    token = client.post("/api/v1/gardens", json={
        "name": "G", "latitude": 52.5, "longitude": 13.4}).json()["share_token"]
    bed = client.post(f"/api/v1/gardens/{token}/beds", json={
        "name": "Beet", "polygon": SQUARE, "soil_type": "loam",
        "moisture": "fresh"}).json()["beds"][0]
    client.post(f"/api/v1/gardens/{token}/recompute")
    return token, int(bed["bed_id"])


def test_a_beds_suggestions_hold_no_parasite(client: TestClient) -> None:
    token, bed_id = _bed(client)
    answer = client.get(f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions",
                        params={"include_light_unsuitable": True,
                                "include_introduced": True}).json()
    names = {i["canonical_name"] for i in answer["items"] + answer["woody"]}
    assert names.isdisjoint(HIDDEN)
    assert set(KEPT) <= names, "the green hemiparasites are sown, and stay"


def test_nor_does_the_catalogue_search(client: TestClient) -> None:
    """A plant nobody can grow is no suggestion anywhere."""
    answer = client.get("/api/v1/plants", params={"light": SITE["ellenberg_l"],
                                                  "moisture": 5.0, "limit": 200}).json()
    names = {i["canonical_name"] for i in answer["items"]}
    assert names.isdisjoint(HIDDEN)
    assert set(KEPT) <= names


def test_nor_do_the_planting_improvements(client: TestClient, conn: sqlite3.Connection) -> None:
    _bed(client)
    garden_id = int(conn.execute("SELECT garden_id FROM garden").fetchone()[0])
    improvements = garden_improvements(conn, load_garden(conn, garden_id))
    added = {c.canonical_name for c in improvements.additions}
    assert added.isdisjoint(HIDDEN)
    assert added & set(KEPT), "something green was worth adding"


def test_the_filter_does_not_count_them(client: TestClient) -> None:
    """Not a filter the gardener set: nothing to report, nothing to switch off."""
    token, bed_id = _bed(client)
    answer = client.get(f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions").json()
    assert answer["total"] == len(KEPT)
    assert all(c["excluded"] == 0 for c in answer["filters"].values())


@pytest.mark.parametrize(
    ("name", "parasitic"),
    [("Orobanche lutea", True), ("Phelipanche ramosa", True), ("Hypopitys monotropa", True),
     ("Epipogium aphyllum", True), ("Corallorhiza trifida", True),
     ("Limodorum abortivum", True), ("Loranthus europaeus", True), ("Neottia nidus", True),
     ("Neottia cordata", False), ("Euphrasia officinalis", False),
     ("Odontites vulgaris", False), ("Pedicularis palustris", False),
     ("Thesium linophyllon", False), ("Lathyrus pratensis", False)],
)
def test_the_list_names_genera_and_the_mixed_ones_by_species(name: str, parasitic: bool) -> None:
    """A genus is matched as a whole word: Lathyrus is not Lathraea."""
    assert is_parasitic(name) is parasitic
