"""Suggestions for a bed — the connection missing since Wave 2."""
import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.web.app import app

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


def _species(c: sqlite3.Connection, tid: int, name: str, light: float,
             form: str | None) -> None:
    c.execute(
        "INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
        (tid, name),
    )
    for key, val in (("ellenberg_l", light), ("ellenberg_m", 5.0), ("ellenberg_n", 5.0)):
        upsert_trait(c, tid, key, value_num=val, source="EIVE-1.0", license="CC-BY-4.0")
    upsert_trait(c, tid, "ellenberg_l_nw", value_num=3.0, source="EIVE-1.0", license="CC-BY-4.0")
    if form is not None:
        upsert_trait(c, tid, "growth_form", value_text=form, source="GIFT", license="CC-BY-4.0")


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    _species(conn, 1, "Sonnenkraut", light=8.0, form="forb")
    _species(conn, 2, "Schattenkraut", light=2.0, form="forb")
    _species(conn, 3, "Riesenbaum", light=8.0, form="tree")
    _species(conn, 4, "Grosstrauch", light=8.0, form="shrub")
    _species(conn, 5, "Unbekanntwuchs", light=8.0, form=None)
    conn.commit()
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _sunny_bed(client: TestClient) -> tuple[str, int]:
    token = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]
    bed = client.post(
        f"/api/v1/gardens/{token}/beds",
        json={"name": "Sonnenbeet", "polygon": SQUARE, "soil_type": "loam", "moisture": "fresh"},
    ).json()["beds"][0]
    client.post(f"/api/v1/gardens/{token}/recompute")
    return token, bed["bed_id"]


def _names(client: TestClient, token: str, bed_id: int, **params: object) -> list[str]:
    response = client.get(f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions", params=params)
    assert response.status_code == 200, response.text
    return [item["canonical_name"] for item in response.json()["items"]]


def test_suggestions_use_the_beds_own_conditions(client: TestClient) -> None:
    """The user never types an Ellenberg number."""
    token, bed_id = _sunny_bed(client)
    names = _names(client, token, bed_id)
    assert names[0] == "Sonnenkraut"
    assert names.index("Sonnenkraut") < names.index("Schattenkraut")


def _woody(client: TestClient, token: str, bed_id: int, **params: object) -> list[str]:
    response = client.get(f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions", params=params)
    assert response.status_code == 200, response.text
    return [item["canonical_name"] for item in response.json()["woody"]]


def test_woody_plants_get_their_own_list_rather_than_being_hidden(
    client: TestClient,
) -> None:
    """Wave 4 hid every woody plant from every bed, and with them the best forage
    plants in the catalogue — Salix caprea leads it with 1,055 German partners.

    Ranking them into the same list did not fix it: they sorted below roughly
    2,000 perennials, which is the same invisibility with a better argument. A
    bed is still a marked area and a tree in it is still just a planting — this
    is a split in how the answer is presented, not a second kind of bed.
    """
    token, bed_id = _sunny_bed(client)
    assert "Riesenbaum" in _woody(client, token, bed_id)
    assert "Grosstrauch" in _woody(client, token, bed_id)


def test_the_main_list_stays_herbaceous(client: TestClient) -> None:
    # Someone planning a 3 m² bed still does not want a hemlock at rank 40.
    token, bed_id = _sunny_bed(client)
    names = _names(client, token, bed_id)
    assert "Sonnenkraut" in names
    assert "Riesenbaum" not in names


def test_woody_plants_can_still_be_switched_off(client: TestClient) -> None:
    # The gate is kept as a choice; it is no longer the default answer.
    token, bed_id = _sunny_bed(client)
    assert _woody(client, token, bed_id, include_trees=False) == []


def test_an_unrecorded_growth_form_is_kept(client: TestClient) -> None:
    """Absent data is not a property of the plant."""
    token, bed_id = _sunny_bed(client)
    assert "Unbekanntwuchs" in _names(client, token, bed_id)


def test_species_already_in_the_bed_are_not_suggested_again(client: TestClient) -> None:
    token, bed_id = _sunny_bed(client)
    assert "Sonnenkraut" in _names(client, token, bed_id)
    client.post(f"/api/v1/gardens/{token}/beds/{bed_id}/plantings", json={"taxon_id": 1})
    assert "Sonnenkraut" not in _names(client, token, bed_id)


def test_planted_species_can_be_included_for_comparison(client: TestClient) -> None:
    token, bed_id = _sunny_bed(client)
    client.post(f"/api/v1/gardens/{token}/beds/{bed_id}/plantings", json={"taxon_id": 1})
    assert "Sonnenkraut" in _names(client, token, bed_id, exclude_planted=False)


def test_each_suggestion_explains_its_fit(client: TestClient) -> None:
    token, bed_id = _sunny_bed(client)
    item = client.get(f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions").json()["items"][0]
    assert item["fit"]["axes"]["ellenberg_l"]["band"] == "optimal"


def test_a_bed_from_another_garden_is_404(client: TestClient) -> None:
    token, bed_id = _sunny_bed(client)
    other = client.post(
        "/api/v1/gardens", json={"name": "Fremd", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]
    response = client.get(f"/api/v1/gardens/{other}/beds/{bed_id}/suggestions")
    assert response.status_code == 404


def test_woodiness_still_identifies_what_growth_form_misses(client: TestClient) -> None:
    """Growth form is absent for part of the catalogue; woodiness covers most of
    the rest. Abies nephrolepis reached a bed's top suggestions through that gap.

    The three signals still combine — they now decide what `include_trees=false`
    removes, rather than what every bed silently never sees.
    """
    conn = app.dependency_overrides[get_connection]()
    _species(conn, 10, "Tannenartig", light=8.0, form=None)
    upsert_trait(conn, 10, "woodiness", value_text="woody", source="GIFT", license="CC-BY-4.0")
    conn.commit()
    token, bed_id = _sunny_bed(client)
    assert "Tannenartig" in _woody(client, token, bed_id)
    assert _woody(client, token, bed_id, include_trees=False) == []


def test_height_identifies_what_neither_form_nor_woodiness_records(
    client: TestClient,
) -> None:
    conn = app.dependency_overrides[get_connection]()
    _species(conn, 11, "Hochgewachsen", light=8.0, form=None)
    upsert_trait(conn, 11, "height_max_m", value_num=12.0, source="GIFT", license="CC-BY-4.0")
    conn.commit()
    token, bed_id = _sunny_bed(client)
    assert "Hochgewachsen" in _woody(client, token, bed_id)


def test_a_species_with_no_woody_signal_at_all_is_still_kept(
    client: TestClient,
) -> None:
    """Absent data is not a property of the plant."""
    token, bed_id = _sunny_bed(client)
    assert "Unbekanntwuchs" in _names(client, token, bed_id)


def test_introduced_species_are_not_suggested_by_default(client: TestClient) -> None:
    """The product promises native plants and a third of the catalogue is not."""
    conn = app.dependency_overrides[get_connection]()
    _species(conn, 20, "Eingefuehrte Art", light=8.0, form="forb")
    upsert_trait(conn, 20, "native_de", value_text="introduced",
                 source="GBIF-WCVP", license="CC-BY-4.0")
    conn.commit()
    token, bed_id = _sunny_bed(client)
    assert "Eingefuehrte Art" not in _names(client, token, bed_id)


def test_introduced_species_can_be_asked_for(client: TestClient) -> None:
    conn = app.dependency_overrides[get_connection]()
    _species(conn, 21, "Auf Wunsch", light=8.0, form="forb")
    upsert_trait(conn, 21, "native_de", value_text="introduced",
                 source="GBIF-WCVP", license="CC-BY-4.0")
    conn.commit()
    token, bed_id = _sunny_bed(client)
    assert "Auf Wunsch" in _names(client, token, bed_id, include_introduced=True)


def test_unknown_origin_is_still_suggested(client: TestClient) -> None:
    """A gap in the data is not a property of the plant."""
    conn = app.dependency_overrides[get_connection]()
    _species(conn, 22, "Herkunft unbekannt", light=8.0, form="forb")
    upsert_trait(conn, 22, "native_de", value_text="unknown",
                 source="GBIF-WCVP", license="CC-BY-4.0")
    conn.commit()
    token, bed_id = _sunny_bed(client)
    assert "Herkunft unbekannt" in _names(client, token, bed_id)


def test_a_species_with_no_origin_record_is_still_suggested(client: TestClient) -> None:
    token, bed_id = _sunny_bed(client)
    assert "Sonnenkraut" in _names(client, token, bed_id)


def _item(client: TestClient, token: str, bed_id: int, name: str,
          **params: object) -> dict[str, object]:
    response = client.get(
        f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions", params=params
    )
    assert response.status_code == 200, response.text
    found = [i for i in response.json()["items"] if i["canonical_name"] == name]
    assert found, f"{name} not among the suggestions"
    return dict(found[0])


def test_a_noted_colour_reaches_the_list_it_was_noted_from(client: TestClient) -> None:
    """Entering a colour and closing the panel used to leave the row saying
    "Farbe unbekannt". It reaches the list because it is now a catalogue trait,
    not because anything is laid over the candidates.
    """
    token, bed_id = _sunny_bed(client)
    assert _item(client, token, bed_id, "Sonnenkraut")["observed_colour"] is None

    client.put(f"/api/v1/gardens/{token}/colours/1", json={"colour": "yellow"})

    row = _item(client, token, bed_id, "Sonnenkraut")
    assert row["observed_colour"] == "yellow"
    assert row["colour_known"] is True
    # And it *is* the colour now, not a value beside it. `observed_colour` still
    # says where it came from, so the panel can mark it as a hand entry.
    assert row["flower_colour"] == "yellow"


def test_a_noted_colour_answers_the_colour_filter(client: TestClient) -> None:
    """Half a fix would show the colour and still not find it: the filter reads
    the same field, so both must see the gardener's answer."""
    token, bed_id = _sunny_bed(client)
    client.put(f"/api/v1/gardens/{token}/colours/1", json={"colour": "yellow"})

    counts = client.get(
        f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions", params={"colour": "yellow"}
    ).json()["filters"]["colour"]
    assert counts["matched"] == 1
    assert _item(client, token, bed_id, "Sonnenkraut", colour="yellow")["fit"] is not None


def test_a_colour_one_gardener_entered_answers_for_everybody(
    client: TestClient,
) -> None:
    """Reversed deliberately, and this test was reversed with it.

    It used to assert the opposite — that an observation stayed in the garden
    that made it — because these were per-garden rows on the volume. They are
    catalogue traits now, marked `manual`: one general database, as asked for.
    The cost is here in plain sight, which is why the test says it rather than
    being deleted.
    """
    mine, my_bed = _sunny_bed(client)
    theirs, their_bed = _sunny_bed(client)
    client.put(f"/api/v1/gardens/{mine}/colours/1", json={"colour": "yellow"})

    assert _item(client, mine, my_bed, "Sonnenkraut")["observed_colour"] == "yellow"
    assert _item(client, theirs, their_bed, "Sonnenkraut")["observed_colour"] == "yellow"
