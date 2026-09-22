"""Buildings drawn as multipolygons reach the plan (2026-09-22).

The query ended in `out tags geom`, and at `tags` Overpass leaves a relation's
members out: every building drawn as a multipolygon — a courtyard building, a
farm range, a house and its barn under one relation — was skipped without a
word. Canned answers in the shape `out geom` gives them.
"""
from __future__ import annotations

from typing import Any

from ninanatur.garden.footprint import covers
from ninanatur.geo.osm import buildings_in
from ninanatur.geo.projection import LatLon, centroid
from ninanatur.geo.surroundings import surroundings_from


def _way(role: str, *corners: tuple[float, float]) -> dict[str, Any]:
    return {"type": "way", "ref": 1, "role": role,
            "geometry": [{"lat": lat, "lon": lon} for lat, lon in corners]}


def _found(*members: dict[str, Any]) -> list[Any]:
    relation = {"type": "relation", "id": 9, "tags": {"building": "yes", "height": "9"},
                "members": list(members)}
    return buildings_in(52.39, 13.19, 52.41, 13.21,
                        fetch=lambda _u, _p=None: {"elements": [relation]})


# A 40 × 40 m square at 52.4 N (about 0.00036° by 0.00059°), and a 20 × 20 m
# courtyard in its middle.
S, N, W, E = 52.40000, 52.40036, 13.20000, 13.20059
CS, CN, CW, CE = 52.40009, 52.40027, 13.200147, 13.200443


def test_an_outer_ring_drawn_as_two_ways_is_one_building() -> None:
    [house] = _found(_way("outer", (S, W), (S, E), (N, E)), _way("outer", (N, E), (N, W), (S, W)))
    assert len(house.outline) == 4
    assert set(house.outline) == {LatLon(S, W), LatLon(S, E), LatLon(N, E), LatLon(N, W)}


def test_a_courtyard_counts_as_building_and_is_recorded() -> None:
    """The outline is the outer ring alone; the courtyard travels beside it. A
    ring with a slit to each courtyard was tried and left: every stroke on the
    plan drew the slit as a wall, and its doubled corners broke editing."""
    [house] = _found(
        _way("outer", (S, W), (S, E), (N, E), (N, W), (S, W)),
        _way("inner", (CS, CW), (CS, CE), (CN, CE), (CN, CW), (CS, CW)),
    )
    ring = [(p.lon, p.lat) for p in house.outline]
    assert covers(ring, ((CW + CE) / 2, (CS + CN) / 2)), "the courtyard is under the outline"
    assert len(house.courtyards) == 1 and len(house.courtyards[0]) == 4


def test_two_separate_parts_are_two_buildings() -> None:
    far = 0.001
    found = _found(
        _way("outer", (S, W), (S, E), (N, E), (N, W), (S, W)),
        _way("outer", (S, W + far), (S, E + far), (N, E + far), (N, W + far), (S, W + far)),
    )
    assert len(found) == 2
    assert all(b.osm_id == 9 and b.tags["height"] == "9" for b in found)


def test_a_garden_in_a_courtyard_is_not_put_under_the_building() -> None:
    """With the courtyard counted as building, a garden in it would stand
    under the house: the house is left out, as before multipolygons arrived."""
    [house] = _found(
        _way("outer", (S, W), (S, E), (N, E), (N, W), (S, W)),
        _way("inner", (CS, CW), (CS, CE), (CN, CE), (CN, CW), (CS, CW)),
    )
    garden = [LatLon(CS + 0.00003, CW + 0.00005), LatLon(CS + 0.00003, CE - 0.00005),
              LatLon(CN - 0.00003, CE - 0.00005), LatLon(CN - 0.00003, CW + 0.00005)]
    assert surroundings_from(centroid(garden), [house], outline=garden).objects == []


def test_a_garden_beside_a_courtyard_building_keeps_it() -> None:
    [house] = _found(
        _way("outer", (S, W), (S, E), (N, E), (N, W), (S, W)),
        _way("inner", (CS, CW), (CS, CE), (CN, CE), (CN, CW), (CS, CW)),
    )
    south = 0.0002  # about 22 m south of the building
    garden = [LatLon(S - south, W), LatLon(S - south, E), LatLon(S - 0.00005, E),
              LatLon(S - 0.00005, W)]
    [placed] = surroundings_from(centroid(garden), [house], outline=garden).objects
    assert placed.osm_id == 9


def test_a_courtyard_touching_the_outer_wall_is_still_recorded() -> None:
    """OpenStreetMap lets an inner ring share a node with the outer; started on
    that node, a test of its first corner alone came out on the wall."""
    mid = (W + E) / 2
    [house] = _found(
        _way("outer", (S, W), (S, E), (N, E), (N, mid), (N, W), (S, W)),
        _way("inner", (N, mid), (CS, CW), (CS, CE), (N, mid)),
    )
    assert len(house.courtyards) == 1
