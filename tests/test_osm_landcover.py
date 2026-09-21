"""The land around a garden, from OpenStreetMap (doc 114): what the answer means.

Canned Overpass answers in the shape `out geom` gives them: a way with its own
`geometry`, a relation with its member ways' geometry under `members`.
"""
from __future__ import annotations

from typing import Any

import pytest

from ninanatur.geo.osm_landcover import (
    KEY_ORDER,
    LANDCOVER,
    assemble,
    kind_of,
    landcover_in,
    landcover_query,
)
from ninanatur.geo.projection import LatLon
from ninanatur.ingest.http import HttpError

CENTRE = LatLon(lat=52.3962, lon=13.2322)
BOX = (52.3947, 13.2298, 52.3977, 13.2346)


def _geometry(*corners: tuple[float, float]) -> list[dict[str, float]]:
    return [{"lat": lat, "lon": lon} for lat, lon in corners]


A, B, C, D = (52.395, 13.230), (52.395, 13.231), (52.396, 13.231), (52.396, 13.230)


def _found(*elements: dict[str, Any]) -> list[Any]:
    return landcover_in(*BOX, centre=CENTRE, fetch=lambda _u, _p=None: {"elements": list(elements)})


def _way(tags: dict[str, str], *corners: tuple[float, float]) -> dict[str, Any]:
    return {"type": "way", "id": 7, "tags": tags, "geometry": _geometry(*corners)}


def _member(role: str, *corners: tuple[float, float]) -> dict[str, Any]:
    return {"type": "way", "ref": 1, "role": role, "geometry": _geometry(*corners)}


def _relation(*members: dict[str, Any], kind: str = "wood") -> dict[str, Any]:
    return {"type": "relation", "id": 9, "tags": {"type": "multipolygon", "natural": kind},
            "members": list(members)}


def test_a_closed_way_is_an_area_of_its_class() -> None:
    [area] = _found(_way({"landuse": "forest"}, A, B, C, D, A))
    assert area.kind == "wood"
    # The ring is closed by meaning, not by repeating its first point.
    assert area.outers == [[LatLon(*A), LatLon(*B), LatLon(*C), LatLon(*D)]]
    assert area.inners == []


def test_a_way_that_does_not_close_is_no_area() -> None:
    """Filled, an open line closes itself with a straight edge across the plan."""
    assert _found(_way({"landuse": "forest"}, A, B, C, D)) == []


@pytest.mark.parametrize(("tags", "kind"), [
    ({"landuse": "meadow"}, "grass"),
    ({"leisure": "park"}, "grass"),
    ({"natural": "scrub"}, "wood"),
    ({"landuse": "reservoir"}, "water"),
    ({"landuse": "orchard"}, "field"),
    ({"landuse": "allotments"}, "allotments"),
    ({"landuse": "farmyard"}, "residential"),
    ({"landuse": "retail"}, "built"),
    ({"amenity": "parking"}, "paved"),
])
def test_every_tag_lands_in_its_class(tags: dict[str, str], kind: str) -> None:
    assert kind_of(tags) == kind


def test_water_is_water_whatever_the_land_around_it_is_called() -> None:
    assert kind_of({"landuse": "residential", "natural": "water"}) == "water"


def test_a_tag_the_plan_does_not_draw_is_left_out() -> None:
    assert kind_of({"landuse": "construction"}) is None
    assert _found(_way({"building": "house"}, A, B, C, A)) == []


def test_a_multipolygon_of_two_member_ways_closes_into_one_ring() -> None:
    """Joined end to end, whichever way round each was drawn."""
    [area] = _found(_relation(_member("outer", A, B, C), _member("outer", A, D, C)))
    [ring] = area.outers
    assert len(ring) == 4
    assert set(ring) == {LatLon(*A), LatLon(*B), LatLon(*C), LatLon(*D)}


def test_a_relation_keeps_its_holes() -> None:
    hole = ((52.3954, 13.2304), (52.3954, 13.2306), (52.3956, 13.2306), (52.3954, 13.2304))
    [area] = _found(_relation(_member("outer", A, B, C, D, A), _member("inner", *hole)))
    assert len(area.outers) == 1
    assert len(area.inners) == 1


def test_a_hole_whose_outer_could_not_close_is_not_drawn_as_land() -> None:
    """One outer closes, one lacks a member; the clearing inside the broken one
    was kept, and filled as wood while the forest around it went blank."""
    far = ((52.400, 13.240), (52.400, 13.241), (52.401, 13.241))
    clearing = ((52.4002, 13.2404), (52.4002, 13.2406), (52.4004, 13.2406), (52.4002, 13.2404))
    [area] = _found(_relation(_member("outer", A, B, C, D, A), _member("outer", *far),
                              _member("inner", *clearing)))
    assert len(area.outers) == 1
    assert area.inners == []


def test_an_outline_that_cannot_be_closed_is_dropped_never_drawn() -> None:
    """A member missing from the answer leaves a gap. Drawn, it would be a wedge."""
    assert _found(_relation(_member("outer", A, B, C))) == []


def test_assembly_keeps_what_closes_and_drops_what_does_not() -> None:
    far = (52.390, 13.220)
    rings = assemble([[LatLon(*A), LatLon(*B)], [LatLon(*B), LatLon(*C), LatLon(*A)],
                      [LatLon(*D), LatLon(*far)]])
    # Where a ring starts is nobody's business; what it goes round is.
    [ring] = rings
    assert len(ring) == 3
    assert set(ring) == {LatLon(*A), LatLon(*B), LatLon(*C)}


def test_only_a_multipolygon_relation_is_an_area() -> None:
    """Any other relation with a landuse tag is a collection, not a boundary."""
    site = _relation(_member("outer", A, B, C, D, A))
    site["tags"]["type"] = "site"
    assert _found(site) == []


def test_a_relation_without_its_members_is_no_area() -> None:
    """What the one live request returned under `out tags geom`: tags and a box."""
    bare = _relation()
    del bare["members"]
    assert _found(bare) == []


@pytest.mark.parametrize("answer", [None, [], "fehler", {"elements": "nein"},
                                    {"elements": [{"type": "way", "tags": {"landuse": "forest"},
                                                   "geometry": [{"lat": "x", "lon": 1}]}]}])
def test_a_malformed_answer_is_no_areas(answer: Any) -> None:
    assert landcover_in(*BOX, centre=CENTRE, fetch=lambda _u, _p=None: answer) == []


def test_an_answer_overpass_gave_up_on_raises() -> None:
    """"Nothing here" would be a claim, and a cached one."""
    gave_up = {"elements": [], "remark": "runtime error: Query timed out"}
    with pytest.raises(HttpError):
        landcover_in(*BOX, centre=CENTRE, fetch=lambda _u, _p=None: gave_up)


def test_the_query_is_built_from_the_table() -> None:
    query = landcover_query(*BOX, CENTRE)
    for key, value in LANDCOVER:
        assert f'"{key}"~"^(' in query and value in query
    assert set(KEY_ORDER) == {key for key, _ in LANDCOVER}


def test_the_query_asks_for_areas_the_garden_lies_inside() -> None:
    """A residential quarter holding the whole box has no outline in it to find."""
    query = landcover_query(*BOX, CENTRE)
    assert "is_in(52.396200,13.232200)->.here;" in query
    assert query.count("(pivot.here)") == 2 * len(KEY_ORDER)


def test_the_query_asks_for_members_not_only_tags() -> None:
    """At `tags` Overpass leaves a relation's members out, and every
    multipolygon with them (the live request, 2026-09-21)."""
    query = landcover_query(*BOX, CENTRE)
    assert query.endswith("out geom;")
    assert "out tags" not in query
