"""Streets from OpenStreetMap, as lines on the plan.

A street does not shade a garden. It is drawn so somebody looking at the plan
knows which way round it is, which means it is drawn and then left alone.
"""
from __future__ import annotations

from typing import Any

from ninanatur.geo.osm import streets_in
from ninanatur.geo.projection import LatLon


def _reply(elements: list[dict[str, Any]]) -> Any:
    def fetch(_url: str, _params: dict[str, str]) -> Any:
        return {"elements": elements}

    return fetch


def test_a_way_becomes_a_centreline() -> None:
    """Geometry, not a centre point: a street is a line and the buildings query
    deliberately asks for centres only."""
    found = streets_in(
        52.5, 13.4, 52.51, 13.41,
        fetch=_reply([
            {
                "id": 1,
                "tags": {"highway": "residential", "name": "Gartenweg"},
                "geometry": [
                    {"lat": 52.500, "lon": 13.400},
                    {"lat": 52.502, "lon": 13.401},
                ],
            }
        ]),
    )
    assert len(found) == 1
    assert found[0].name == "Gartenweg"
    assert found[0].centreline == [
        LatLon(lat=52.500, lon=13.400),
        LatLon(lat=52.502, lon=13.401),
    ]


def test_the_width_follows_the_kind() -> None:
    """A motorway and a footpath are not the same line. The numbers are rough
    on purpose — OSM records a width for almost nothing, and a plan needs a
    plausible one rather than a surveyed one."""
    kinds = [
        {"id": 1, "tags": {"highway": "footway"}, "geometry": [
            {"lat": 52.5, "lon": 13.4}, {"lat": 52.501, "lon": 13.4}]},
        {"id": 2, "tags": {"highway": "residential"}, "geometry": [
            {"lat": 52.5, "lon": 13.4}, {"lat": 52.501, "lon": 13.4}]},
        {"id": 3, "tags": {"highway": "primary"}, "geometry": [
            {"lat": 52.5, "lon": 13.4}, {"lat": 52.501, "lon": 13.4}]},
    ]
    widths = [s.width_m for s in streets_in(52.5, 13.4, 52.51, 13.41, fetch=_reply(kinds))]
    assert widths == sorted(widths)
    assert widths[0] < widths[-1]


def test_a_recorded_width_wins_over_the_guess() -> None:
    found = streets_in(
        52.5, 13.4, 52.51, 13.41,
        fetch=_reply([{
            "id": 1, "tags": {"highway": "residential", "width": "7.5"},
            "geometry": [{"lat": 52.5, "lon": 13.4}, {"lat": 52.501, "lon": 13.4}],
        }]),
    )
    assert found[0].width_m == 7.5


def test_a_way_without_geometry_is_skipped() -> None:
    """Overpass answers what it has. A street with no line is not a street."""
    assert streets_in(
        52.5, 13.4, 52.51, 13.41,
        fetch=_reply([{"id": 1, "tags": {"highway": "residential"}}]),
    ) == []


def test_a_single_point_is_not_a_line() -> None:
    assert streets_in(
        52.5, 13.4, 52.51, 13.41,
        fetch=_reply([{
            "id": 1, "tags": {"highway": "residential"},
            "geometry": [{"lat": 52.5, "lon": 13.4}],
        }]),
    ) == []


def test_a_nameless_track_still_counts() -> None:
    """Most ways have no name. Drawing only the named ones would leave the
    lane the garden actually sits on off the plan."""
    found = streets_in(
        52.5, 13.4, 52.51, 13.41,
        fetch=_reply([{
            "id": 1, "tags": {"highway": "track"},
            "geometry": [{"lat": 52.5, "lon": 13.4}, {"lat": 52.501, "lon": 13.4}],
        }]),
    )
    assert len(found) == 1
    assert found[0].name is None


def test_a_bad_answer_is_no_streets_rather_than_a_crash() -> None:
    """Overpass is a free service with no SLA. A garden must still be made."""
    assert streets_in(52.5, 13.4, 52.51, 13.41, fetch=lambda _u, _p: "kaputt") == []
