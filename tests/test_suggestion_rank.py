"""Suggestions ranked by the best growing conditions, then insect value (owner, 2026-09-21).

"Für die Sonnenstunden/Schatten die best passendste Pflanze … nach besten
Wachstumsbedingungen + Insektenwert gerankt." A shade bed is led by shade
plants and a sunny one by sun plants; among plants that grow equally well the
insects decide; and no number of insects buys a clearly worse fit a place
above a good one.
"""
from __future__ import annotations

import math
import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.bloom import improve
from ninanatur.fit.rank import (
    OPTIMAL_AXIS_SCORE,
    growing_conditions,
    insect_value,
    insect_weight,
    suggestion_rank,
)
from ninanatur.fit.score import BAND_EDGES, SiteVector, SpeciesNiche, score_species
from ninanatur.garden.store import load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.solar.light import SUN_HOUR_ANCHORS
from ninanatur.web.app import app

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]
EIVE = {"source": "EIVE-1.0", "license": "CC-BY-4.0"}
SOIL = {"ellenberg_m": 5.0, "ellenberg_n": 5.5, "ellenberg_r": 6.5}
FULL_SUN = SUN_HOUR_ANCHORS[-1][1]
DEEP_SHADE = SUN_HOUR_ANCHORS[0][1]
#: One width for every species' light, so only the distance differs: a half
#: width of 1.5, so 0.75 away is the optimal band's edge.
WIDTH = 3.0


# --- the arithmetic -----------------------------------------------------------

def _fit(light: float, target: float = 5.0, **more: float) -> tuple[float, float]:
    site = SiteVector(values={"ellenberg_l": target, **SOIL, **more})
    niche = SpeciesNiche(1, {"ellenberg_l": light, **SOIL, **more}, {"ellenberg_l": WIDTH})
    fit = score_species(site, niche)
    return fit.score or 0.0, growing_conditions(fit, len(site.values))


def test_every_axis_inside_the_optimal_band_grows_perfectly() -> None:
    """0.99 and 0.93 are the same answer inside EIVE's precision."""
    edge = BAND_EDGES[0] * WIDTH / 2
    close, far = _fit(5.0), _fit(5.0 + edge * 0.99)
    assert close[1] == far[1] == 1.0
    assert close[0] > far[0], "the plain fit still tells them apart, for ties"


def test_outside_the_optimal_band_growing_falls_with_the_fit() -> None:
    values = [_fit(5.0 + d)[1] for d in (0.8, 1.2, 1.6, 2.2, 3.0)]
    assert values == sorted(values, reverse=True)
    assert values[0] < 1.0


def test_an_unrecorded_axis_keeps_a_species_below_perfect() -> None:
    """The neutral middle, as in `score_species`: a less documented species is
    not a better fit."""
    site = SiteVector(values={"ellenberg_l": 5.0, **SOIL})
    niche = SpeciesNiche(1, {"ellenberg_l": 5.0, "ellenberg_m": 5.0, "ellenberg_n": 5.5})
    assert growing_conditions(score_species(site, niche), len(site.values)) < 1.0


def test_insect_value_is_a_log_scale_over_the_catalogues_range() -> None:
    assert insect_value(None, 1055) == insect_value(0, 1055) == 0.0
    assert insect_value(1055, 1055) == 1.0
    assert insect_value(67, 1055) == pytest.approx(math.log(68) / math.log(1056))
    assert insect_value(10, 1055) - insect_value(9, 1055) > (
        insect_value(1000, 1055) - insect_value(999, 1055)
    ), "the tenth partner means more than the thousandth"
    # Each tenfold counts alike, wherever it happens (log1p: 9 -> 99 -> 999).
    assert insect_value(99, 1055) - insect_value(9, 1055) == pytest.approx(
        insect_value(999, 1055) - insect_value(99, 1055))
    assert insect_value(5, 0) == 0.0


#: Four axes for a bed, five for GET /plants when it is given a temperature.
AXES_ASKED = pytest.mark.parametrize("more", [{}, {"ellenberg_t": 5.0}], ids=["4 axes", "5 axes"])


@AXES_ASKED
def test_a_borderline_axis_never_beats_an_all_optimal_plant_whatever_its_insects(
    more: dict[str, float],
) -> None:
    """The weight's reason: with the catalogue's top count a plant climbs over
    an all-optimal one with none only while its one off axis is *suitable* —
    not a hair past the band edge, and not with five axes either (review,
    2026-09-21: at a flat 0.1 both went through)."""
    axes = 4 + len(more)
    half = WIDTH / 2
    best = suggestion_rank(_fit(5.0, **more)[1], insect_value(0, 1055), axes)
    assert suggestion_rank(_fit(5.0 + 0.99 * half, **more)[1], 1.0, axes) > best
    for past in (1.003, 1.02, 1.09):
        assert suggestion_rank(_fit(5.0 + past * half, **more)[1], 1.0, axes) < best


@pytest.mark.parametrize("axes", [1, 2, 3, 4, 5])
def test_the_weight_is_the_end_of_suitable(axes: int) -> None:
    """Derived rather than asserted: a plant with one axis at the suitable
    edge, lifted by the full weight, meets an all-optimal plant exactly."""
    edge = math.exp(-0.5 * BAND_EDGES[1] ** 2) / OPTIMAL_AXIS_SCORE
    assert edge ** (1 / axes) * (1 + insect_weight(axes)) == pytest.approx(1.0, abs=1e-12)
    assert insect_weight(0) == 0.0


def test_a_typical_count_needs_an_axis_well_inside_suitable() -> None:
    """The docstring's second promise: against an all-optimal plant with the
    catalogue's median count, the top count helps only below z = 0.74."""
    half = WIDTH / 2
    typical = suggestion_rank(1.0, insect_value(67, 1055), 4)
    assert suggestion_rank(_fit(5.0 + 0.73 * half)[1], 1.0, 4) > typical
    assert suggestion_rank(_fit(5.0 + 0.75 * half)[1], 1.0, 4) < typical


# --- a bed's list ------------------------------------------------------------

def _species(c: sqlite3.Connection, tid: int, name: str, light: float, partners: int) -> None:
    c.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
              (tid, name))
    for key, value in SOIL.items():
        upsert_trait(c, tid, key, value_num=value, **EIVE)
    upsert_trait(c, tid, "ellenberg_l", value_num=light, **EIVE)
    upsert_trait(c, tid, "ellenberg_l_nw", value_num=WIDTH, **EIVE)
    upsert_trait(c, tid, "growth_form", value_text="forb", source="GIFT", license="CC-BY-4.0")
    upsert_trait(c, tid, "native_de", value_text="native", source="GBIF-WCVP",
                 license="CC-BY-4.0")
    for key, month in (("flowering_start_month", 5.0), ("flowering_end_month", 5.0)):
        upsert_trait(c, tid, key, value_num=month, source="GIFT", license="CC-BY-4.0")
    c.execute("INSERT INTO partner_totals (taxon_id, german, global_total, unmatched)"
              " VALUES (?, ?, ?, 0)", (tid, partners, partners))


#: name, L, German insect partners. Optimal is within 0.75 of the bed's L.
SPECIES = (
    ("Schattenkraut", DEEP_SHADE, 10),        # perfect in shade, few insects
    ("Waldkraut", DEEP_SHADE + 0.5, 300),     # optimal in shade, many
    ("Grenzkraut", DEEP_SHADE + 1.8, 5000),   # borderline in shade, the most
    ("Sonnenkraut", FULL_SUN, 10),            # perfect in sun, few
    ("Wiesenkraut", FULL_SUN - 0.5, 300),     # optimal in sun, many
    ("Mittelkraut", 5.8, 800),                # half shade: unsuitable at both ends
)


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    c = connect(":memory:", same_thread=False)
    init_schema(c)
    for tid, (name, light, partners) in enumerate(SPECIES, start=1):
        _species(c, tid, name, light, partners)
    c.commit()
    yield c


@pytest.fixture()
def client(conn: sqlite3.Connection) -> Iterator[TestClient]:
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _bed(client: TestClient, conn: sqlite3.Connection, light: float) -> tuple[str, int]:
    """An open bed on loam, its light computed, then set: the list is under
    test here, not the shadow model."""
    token = client.post("/api/v1/gardens", json={
        "name": "G", "latitude": 52.5, "longitude": 13.4}).json()["share_token"]
    bed = client.post(f"/api/v1/gardens/{token}/beds", json={
        "name": "Beet", "polygon": SQUARE, "soil_type": "loam",
        "moisture": "fresh"}).json()["beds"][0]
    client.post(f"/api/v1/gardens/{token}/recompute")
    conn.execute("UPDATE element SET ellenberg_l = ? WHERE element_id = ?",
                 (light, bed["bed_id"]))
    conn.commit()
    return token, int(bed["bed_id"])


def _list(client: TestClient, token: str, bed_id: int) -> list[dict[str, Any]]:
    answer = client.get(f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions").json()
    return list(answer["items"])


def test_a_deep_shade_bed_is_led_by_shade_plants(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    names = [i["canonical_name"] for i in _list(client, *_bed(client, conn, DEEP_SHADE))]
    assert names[:2] == ["Waldkraut", "Schattenkraut"]
    assert "Sonnenkraut" not in names and "Wiesenkraut" not in names


def test_a_full_sun_bed_is_led_by_sun_plants(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    names = [i["canonical_name"] for i in _list(client, *_bed(client, conn, FULL_SUN))]
    assert names == ["Wiesenkraut", "Sonnenkraut"]


def test_among_equally_good_fits_the_insects_decide(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    """Both optimal; the one that fits a hair better but feeds 10 species comes
    after the one that feeds 300."""
    items = _list(client, *_bed(client, conn, DEEP_SHADE))
    wald, schatten = items[0], items[1]
    assert wald["fit"]["score"] < schatten["fit"]["score"]
    assert (wald["insect_partners"], schatten["insect_partners"]) == (300, 10)


def test_a_poor_fit_with_the_most_insects_does_not_beat_a_good_fit(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    items = _list(client, *_bed(client, conn, DEEP_SHADE))
    names = [i["canonical_name"] for i in items]
    grenz = items[names.index("Grenzkraut")]
    assert grenz["fit"]["axes"]["ellenberg_l"]["band"] == "borderline"
    assert grenz["insect_partners"] == 5000
    assert names.index("Grenzkraut") > names.index("Schattenkraut")


def test_the_improvements_weigh_the_same_order(
    client: TestClient, conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With room for one candidate, the one that grows as well and feeds more
    is weighed — not the plain fit's favourite."""
    monkeypatch.setattr(improve, "CANDIDATE_POOL", 1)
    _bed(client, conn, DEEP_SHADE)
    garden_id = int(conn.execute("SELECT garden_id FROM garden").fetchone()[0])
    added = improve.garden_improvements(conn, load_garden(conn, garden_id)).additions
    assert [c.canonical_name for c in added] == ["Waldkraut"]
