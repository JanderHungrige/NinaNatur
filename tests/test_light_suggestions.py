"""Suggestions and the light — the owner's review item #9 (2026-09-21).

"Half-shade plants should not be placed in full sun" — and, the same day, "not
only sun but also shade". A bed whose light is unsuitable for a species, too
bright or too dark, does not offer it; the woody shortlist takes only what the
light suits; and the answer says whether there was a light value to judge by.

The named woodland species carry their real EIVE 1.0 values from the shipped
catalogue. The rest share the bed's soil values, so only their light differs.
"""
import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.solar.light import SUN_HOUR_ANCHORS
from ninanatur.web.app import app

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]
EIVE = {"source": "EIVE-1.0", "license": "CC-BY-4.0"}
# Loam, fresh: what `site_axes_from_soil` gives the bed.
SOIL = {"ellenberg_m": 5.0, "ellenberg_n": 5.5, "ellenberg_r": 6.5}
# The ends of the light model (`SUN_HOUR_ANCHORS`): full sun and deep shade.
FULL_SUN = SUN_HOUR_ANCHORS[-1][1]
DEEP_SHADE = SUN_HOUR_ANCHORS[0][1]


def _species(c: sqlite3.Connection, tid: int, name: str, light: tuple[float, float] | None,
             *, form: str = "forb", partners: int = 0, **axes: float) -> None:
    c.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
              (tid, name))
    for key, value in {**SOIL, **axes}.items():
        upsert_trait(c, tid, key, value_num=value, **EIVE)
    if light is not None:
        upsert_trait(c, tid, "ellenberg_l", value_num=light[0], **EIVE)
        upsert_trait(c, tid, "ellenberg_l_nw", value_num=light[1], **EIVE)
    upsert_trait(c, tid, "growth_form", value_text=form, source="GIFT", license="CC-BY-4.0")
    if partners:
        c.execute("INSERT INTO partner_totals (taxon_id, german, global_total, unmatched)"
                  " VALUES (?, ?, ?, 0)", (tid, partners, partners))


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    # Real EIVE values: L, its niche width, then M, N, R.
    _species(conn, 1, "Galium odoratum", (1.66, 5.29),
             ellenberg_m=4.59, ellenberg_n=5.44, ellenberg_r=6.24)
    _species(conn, 2, "Pulmonaria officinalis", (4.06, 4.40),
             ellenberg_m=4.63, ellenberg_n=6.12, ellenberg_r=7.38)
    _species(conn, 3, "Carex sylvatica", (2.26, 6.47))
    _species(conn, 4, "Sonnenstaude", (8.0, 3.0))
    _species(conn, 5, "Ohne Lichtwert", None)
    _species(conn, 6, "Lichthungrig", (7.82, 2.49))
    # Woody, with their real L and German insect partners: by value alone the
    # two sun shrubs would lead a deep-shade bed's shortlist.
    _species(conn, 10, "Salix caprea", (6.52, 6.81), form="shrub", partners=1055)
    _species(conn, 11, "Salix repens", (7.77, 3.05), form="shrub", partners=947)
    _species(conn, 12, "Prunus spinosa", (7.09, 3.70), form="shrub", partners=771)
    _species(conn, 13, "Hedera helix", (3.89, 7.96), form="shrub", partners=444)
    _species(conn, 14, "Taxus baccata", (3.39, 6.29), form="tree", partners=42)
    _species(conn, 15, "Schattenstrauch", (2.0, 3.0), form="shrub", partners=2000)
    conn.commit()
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _bed(client: TestClient, *, lit: bool = True) -> tuple[str, int]:
    """An open 16 m² bed. With `lit` the light is computed: full sun."""
    token = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]
    bed = client.post(
        f"/api/v1/gardens/{token}/beds",
        json={"name": "Beet", "polygon": SQUARE, "soil_type": "loam", "moisture": "fresh"},
    ).json()["beds"][0]
    if lit:
        garden = client.post(f"/api/v1/gardens/{token}/recompute").json()
        assert garden["beds"][0]["ellenberg_l"] == FULL_SUN, "the fixture needs full sun"
    return token, int(bed["bed_id"])


def _deep_shade(client: TestClient) -> tuple[str, int]:
    """The same bed, its light set to the model's deepest rung.

    Set rather than built from walls: what is under test is what the list does
    with a value, not the shadow model, which has its own tests.
    """
    token, bed_id = _bed(client)
    conn = app.dependency_overrides[get_connection]()
    conn.execute("UPDATE element SET ellenberg_l = ? WHERE element_id = ?", (DEEP_SHADE, bed_id))
    conn.commit()
    return token, bed_id


def _ask(client: TestClient, token: str, bed_id: int, **params: object) -> dict[str, Any]:
    response = client.get(
        f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions", params={"limit": 100, **params}
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def _names(answer: dict[str, Any], key: str = "items") -> list[str]:
    return [item["canonical_name"] for item in answer[key]]


# --- too bright is left out ------------------------------------------------

def test_a_full_sun_bed_does_not_offer_woodland_herbs(client: TestClient) -> None:
    """The owner's example: half-shade plants do not belong in full sun."""
    names = _names(_ask(client, *_bed(client)))
    assert "Galium odoratum" not in names
    assert "Pulmonaria officinalis" not in names
    assert "Sonnenstaude" in names


def test_what_the_light_left_out_is_counted(client: TestClient) -> None:
    """So the list can say "N Arten wegen Licht ausgeblendet" rather than hide it."""
    light = _ask(client, *_bed(client))["filters"]["light"]
    # Galium, Pulmonaria and Carex sylvatica; Schattenstrauch and Taxus too — the count is
    # over every candidate, woody ones included.
    assert light["excluded"] == 5
    assert light["unknown"] == 1  # Ohne Lichtwert, kept


def test_they_can_still_be_asked_for_and_rank_below(client: TestClient) -> None:
    answer = _ask(client, *_bed(client), include_light_unsuitable=True)
    names = _names(answer)
    assert names.index("Sonnenstaude") < names.index("Pulmonaria officinalis")
    assert "Galium odoratum" in names
    assert "light" not in answer["filters"], "an opted-out cut must not claim removals"


def test_a_species_with_no_light_value_is_kept(client: TestClient) -> None:
    """Unknown is not a mismatch, and `include_unknown` is not needed for it."""
    assert "Ohne Lichtwert" in _names(_ask(client, *_bed(client)))


# --- too dark is left out too -------------------------------------------------

def test_a_deep_shade_bed_does_not_offer_sun_plants(client: TestClient) -> None:
    """The owner's second word on it: the best fit for the shade as much as for
    the sun. Ranked down, sun plants filled a shade bed's list whenever filters
    narrowed it."""
    answer = _ask(client, *_deep_shade(client))
    names = _names(answer)
    assert "Lichthungrig" not in names
    assert "Sonnenstaude" not in names
    assert {"Carex sylvatica", "Galium odoratum", "Ohne Lichtwert"} <= set(names)
    assert answer["filters"]["light"]["excluded"] >= 2


def test_the_opt_out_brings_both_directions_back_ranked_below(client: TestClient) -> None:
    for bed, fits, misfit in ((_deep_shade, "Carex sylvatica", "Lichthungrig"),
                              (_bed, "Sonnenstaude", "Galium odoratum")):
        answer = _ask(client, *bed(client), include_light_unsuitable=True)
        names = _names(answer)
        shown = next(i for i in answer["items"] if i["canonical_name"] == misfit)
        assert shown["fit"]["axes"]["ellenberg_l"]["band"] == "unsuitable"
        assert names.index(fits) < names.index(misfit)
        assert "light" not in answer["filters"]


# --- the woody shortlist -----------------------------------------------------

def _light_bands(answer: dict[str, Any]) -> list[str]:
    return [i["fit"]["axes"]["ellenberg_l"]["band"] for i in answer["woody"]]


def test_the_woody_shortlist_in_deep_shade_holds_no_sun_shrub(client: TestClient) -> None:
    """Ordered by animal value, it once gave every bed the same willows."""
    answer = _ask(client, *_deep_shade(client))
    woody = _names(answer, "woody")
    assert "Salix repens" not in woody
    assert "Prunus spinosa" not in woody
    assert "unsuitable" not in _light_bands(answer)


def test_the_woody_shortlist_respects_fit_before_partners(client: TestClient) -> None:
    """Salix caprea, the catalogue's most visited plant, is *borderline* on
    light in deep shade; Hedera and Taxus are optimal there. Partners no longer
    buy the willow a place above them — among the shrubs that grow well, the
    one insects visit most still leads."""
    answer = _ask(client, *_deep_shade(client))
    woody = _names(answer, "woody")
    bands = dict(zip(woody, _light_bands(answer), strict=True))
    assert bands["Salix caprea"] == "borderline"
    assert bands["Hedera helix"] == bands["Taxus baccata"] == "optimal"
    assert woody == ["Schattenstrauch", "Hedera helix", "Taxus baccata", "Salix caprea"]


def test_the_opt_out_widens_the_shortlist_too_ranked_below(client: TestClient) -> None:
    """The shortlist follows the main list's order now, so the opt-out means
    the same there: what the light does not suit comes back, below the rest."""
    token, bed_id = _bed(client)
    assert "Schattenstrauch" not in _names(_ask(client, token, bed_id), "woody")

    answer = _ask(client, token, bed_id, include_light_unsuitable=True)
    bands = _light_bands(answer)
    assert _names(answer, "woody")[-1] == "Schattenstrauch", "2,000 partners, the wrong light"
    first_misfit = bands.index("unsuitable")
    assert all(band == "unsuitable" for band in bands[first_misfit:])


# --- whether there was a light to judge by ---------------------------------

def test_a_bed_whose_light_was_never_computed_says_so(client: TestClient) -> None:
    answer = _ask(client, *_bed(client, lit=False))
    assert answer["light_state"] == "missing"
    assert "ellenberg_l" not in answer["site_axes"]
    assert "light" not in answer["filters"], "nothing to cut by"
    assert "Galium odoratum" in _names(answer), "ranked on the soil alone"


def test_a_freshly_computed_bed_is_current(client: TestClient) -> None:
    assert _ask(client, *_bed(client))["light_state"] == "current"


def test_a_new_obstacle_makes_the_light_stale(client: TestClient) -> None:
    token, bed_id = _bed(client)
    client.post(f"/api/v1/gardens/{token}/obstacles",
                json={"kind": "wall", "x": 2.0, "y": -2.0, "shape": "rect",
                      "width": 6.0, "depth": 0.4, "height": 3.0})
    assert _ask(client, token, bed_id)["light_state"] == "stale"


def test_a_light_value_with_no_map_behind_it_is_stale(client: TestClient) -> None:
    """Nothing says what it was computed from, so nothing vouches for it."""
    token, bed_id = _bed(client)
    conn = app.dependency_overrides[get_connection]()
    conn.execute("DELETE FROM light_grid")
    conn.commit()
    assert _ask(client, token, bed_id)["light_state"] == "stale"


def test_the_list_and_the_sun_map_agree_on_what_is_stale(client: TestClient) -> None:
    """Two copies of one comparison — the map's `stale`, the list's `light_state`
    — so what one says the other must say too."""
    token, bed_id = _bed(client)
    for step in ("just computed", "a wall since"):
        stale = client.get(f"/api/v1/gardens/{token}/light").json()["stale"]
        assert (_ask(client, token, bed_id)["light_state"] == "stale") is stale, step
        client.post(f"/api/v1/gardens/{token}/obstacles",
                    json={"kind": "wall", "x": 2.0, "y": -2.0, "shape": "rect",
                          "width": 6.0, "depth": 0.4, "height": 3.0})


def test_changing_the_soil_does_not_make_the_light_stale(client: TestClient) -> None:
    """The map's own test: soil moves no shadow, so it is not a reason to relight."""
    token, bed_id = _bed(client)
    client.patch(f"/api/v1/gardens/{token}/beds/{bed_id}", json={"moisture": "moist"})
    assert _ask(client, token, bed_id)["light_state"] == "current"
