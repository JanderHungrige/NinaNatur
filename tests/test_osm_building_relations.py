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
from ninanatur.geo.osm_rings import with_holes
from ninanatur.geo.projection import LatLon, centroid, to_metres
from ninanatur.geo.surroundings import surroundings_from
from ninanatur.solar.position import SunPosition
from ninanatur.solar.shading import Obstacle, Point, is_shaded


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


def test_a_courtyard_stays_open_ground() -> None:
    [house] = _found(
        _way("outer", (S, W), (S, E), (N, E), (N, W), (S, W)),
        _way("inner", (CS, CW), (CS, CE), (CN, CE), (CN, CW), (CS, CW)),
    )
    ring = [(p.lon, p.lat) for p in house.outline]
    assert covers(ring, (W + 0.00005, S + 0.00005)), "a wing is the building"
    assert not covers(ring, ((CW + CE) / 2, (CS + CN) / 2)), "the courtyard is not"


def test_two_separate_parts_are_two_buildings() -> None:
    far = 0.001
    found = _found(
        _way("outer", (S, W), (S, E), (N, E), (N, W), (S, W)),
        _way("outer", (S, W + far), (S, E + far), (N, E + far), (N, W + far), (S, W + far)),
    )
    assert len(found) == 2
    assert all(b.osm_id == 9 and b.tags["height"] == "9" for b in found)


def test_a_courtyard_imported_gets_its_sun() -> None:
    """Through the import's own placing: the courtyard of a 9 m house, the sun
    high in the south — open sky over it, where the whole square was shade."""
    [house] = _found(
        _way("outer", (S, W), (S, E), (N, E), (N, W), (S, W)),
        _way("inner", (CS, CW), (CS, CE), (CN, CE), (CN, CW), (CS, CW)),
    )
    anchor = centroid(house.outline)
    [placed] = surroundings_from(anchor, [house], outline=house.outline).objects
    footprint = [(float(x), float(y)) for x, y in placed.outline]
    middle = to_metres(LatLon((CS + CN) / 2, (CW + CE) / 2), anchor)
    assert not is_shaded(Point(middle.x, middle.y), Obstacle(footprint=footprint, height=9.0),
                         SunPosition(altitude=60.0, azimuth=180.0))


def test_a_hole_turns_the_other_way_whichever_way_it_was_drawn() -> None:
    outer = [LatLon(S, W), LatLon(S, E), LatLon(N, E), LatLon(N, W)]
    hole = [LatLon(CS, CW), LatLon(CS, CE), LatLon(CN, CE), LatLon(CN, CW)]
    for drawn in (hole, list(reversed(hole))):
        ring = [(p.lon, p.lat) for p in with_holes(outer, [drawn])]
        assert not covers(ring, ((CW + CE) / 2, (CS + CN) / 2))
        assert len(ring) == len(outer) + len(hole) + 2, "a slit there and back"
