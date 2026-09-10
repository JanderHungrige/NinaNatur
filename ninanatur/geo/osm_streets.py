"""Streets from OpenStreetMap, as centrelines with a width.

Split from `osm.py` when refusing Overpass's incomplete answers took that file
past the 300-line limit. The streets are their own concern — a line and a width
for the plan — and already had their own tests.
"""
from __future__ import annotations

from dataclasses import dataclass

from ninanatur.geo.osm import OVERPASS, Fetch, complete_or_fail, fetch_overpass
from ninanatur.geo.projection import LatLon

#: Rough carriageway widths in metres, by `highway` value.
#:
#: Rough on purpose: OSM records a width for almost nothing, and a plan needs a
#: plausible line rather than a surveyed one. A recorded `width` always wins.
STREET_WIDTHS: dict[str, float] = {
    "footway": 1.5,
    "path": 1.5,
    "cycleway": 2.0,
    "track": 3.0,
    "service": 3.5,
    "living_street": 5.0,
    "residential": 6.0,
    "unclassified": 6.0,
    "tertiary": 7.0,
    "secondary": 8.0,
    "primary": 10.0,
}

DEFAULT_STREET_WIDTH_M = 5.0


@dataclass(frozen=True)
class OsmStreet:
    """A way, as a centreline and a width — which is what an `element` stores."""

    osm_id: int
    name: str | None
    centreline: list[LatLon]
    width_m: float


def _street_query(south: float, west: float, north: float, east: float) -> str:
    # `out geom` rather than `out center`: a street is a line, and its shape is
    # the whole of what makes it useful on a plan. Buildings ask for centres
    # precisely because their shape is not needed there.
    kinds = "|".join(STREET_WIDTHS)
    return (
        f"[out:json][timeout:40];"
        f'way["highway"~"^({kinds})$"]({south},{west},{north},{east});'
        f"out geom;"
    )


def streets_in(
    south: float, west: float, north: float, east: float, *, fetch: Fetch = fetch_overpass
) -> list[OsmStreet]:
    """Ways in the box, as centrelines.

    Overpass is a free service with no SLA, the same standing as Nominatim. A
    malformed answer is no streets rather than an exception: the garden still
    has to be made. An answer Overpass itself says it gave up on is different —
    that raises, because "no streets" would be a claim, and a cached one.
    """
    raw = complete_or_fail(fetch(OVERPASS, {"data": _street_query(south, west, north, east)}))
    if not isinstance(raw, dict):
        return []

    found: list[OsmStreet] = []
    for element in raw.get("elements", []):
        geometry = element.get("geometry") or []
        # Two points are the fewest that make a line. Overpass answers what it
        # has, and a street without one is not a street.
        if len(geometry) < 2:
            continue
        tags = {str(k): str(v) for k, v in (element.get("tags") or {}).items()}
        found.append(
            OsmStreet(
                osm_id=int(element.get("id", 0)),
                # Most ways have no name. Drawing only the named ones would
                # leave the lane the garden sits on off the plan.
                name=tags.get("name"),
                centreline=[
                    LatLon(lat=float(p["lat"]), lon=float(p["lon"])) for p in geometry
                ],
                width_m=_street_width(tags),
            )
        )
    return found


def _street_width(tags: dict[str, str]) -> float:
    recorded = tags.get("width")
    if recorded is not None:
        try:
            return float(recorded)
        except ValueError:
            # "ca. 6 m" and friends. A guess beats refusing to draw the street.
            pass
    return STREET_WIDTHS.get(tags.get("highway", ""), DEFAULT_STREET_WIDTH_M)


__all__ = ["DEFAULT_STREET_WIDTH_M", "STREET_WIDTHS", "OsmStreet", "streets_in"]
