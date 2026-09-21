"""What the ground around a garden is, from OpenStreetMap (doc 114).

Woods, fields, water, parks, allotments and built-up land, as areas the plan
colours its surroundings with. Modelled on `osm_streets.py`: one Overpass query,
built from one table, through the same refusal of an answer Overpass itself gave
up on. The areas are OpenStreetMap's, ODbL-1.0, and the plan credits them
(`garden/credits.py`).

Only the parsing is here: what the rings are, in degrees. Turning them into
garden metres and cutting them to the plan is `landcover_clip.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeGuard

from ninanatur.geo.osm import OVERPASS, Fetch, complete_or_fail, overpass_complete
from ninanatur.geo.projection import LatLon
from ninanatur.ingest.http import get_json

#: OpenStreetMap's tags, and the few classes the plan draws them as.
#:
#: Few on purpose. The plan is about a garden; around it, a reader needs to see
#: "wood", "field", "water", "houses" — not the forty values `landuse` takes.
LANDCOVER: dict[tuple[str, str], str] = {
    ("landuse", "grass"): "grass",
    ("landuse", "meadow"): "grass",
    ("landuse", "village_green"): "grass",
    ("landuse", "recreation_ground"): "grass",
    ("landuse", "cemetery"): "grass",
    ("leisure", "park"): "grass",
    ("leisure", "pitch"): "grass",
    ("natural", "grassland"): "grass",
    ("natural", "heath"): "grass",
    ("landuse", "forest"): "wood",
    ("natural", "wood"): "wood",
    ("natural", "scrub"): "wood",
    ("natural", "water"): "water",
    ("landuse", "basin"): "water",
    ("landuse", "reservoir"): "water",
    ("landuse", "farmland"): "field",
    ("landuse", "orchard"): "field",
    ("landuse", "vineyard"): "field",
    ("landuse", "allotments"): "allotments",
    ("leisure", "garden"): "allotments",
    ("landuse", "residential"): "residential",
    ("landuse", "farmyard"): "residential",
    ("landuse", "commercial"): "built",
    ("landuse", "retail"): "built",
    ("landuse", "industrial"): "built",
    ("amenity", "parking"): "paved",
}

#: Which key decides when an area carries two: water is water whatever
#: `landuse` says around it, and a park's `landuse=grass` is the more exact word.
KEY_ORDER = ("natural", "landuse", "leisure", "amenity")

#: The most an answer may be. One forest relation arrives with its whole
#: outline, however far past the garden it runs; a town's worth of them is still
#: far below this, and an answer past it is refused rather than read.
LANDCOVER_MAX_BYTES = 20_000_000

#: Seconds Overpass may spend, and the read timeout that covers it. Shorter
#: than the buildings' 40: this is decoration, and a garden should not wait
#: long for the colour of its neighbourhood.
QUERY_TIMEOUT_S = 25
READ_TIMEOUT: tuple[float, float] = (5.0, 30.0)

#: Roles that bound a multipolygon's area. An empty role is an outer by old
#: convention, and OpenStreetMap still holds some.
OUTER_ROLES = ("outer", "")


@dataclass(frozen=True)
class OsmArea:
    """One area: its class, and its rings — closed, the last point not repeated."""

    osm_id: int
    kind: str
    outers: list[list[LatLon]]
    inners: list[list[LatLon]]


def fetch_landcover(url: str, params: dict[str, Any] | None = None) -> Any:
    """The live fetch: capped, one attempt, and refusing an answer Overpass
    gave up on before it can be cached. Decoration is not worth three tries
    and seven seconds of back-off while Overpass is struggling (review)."""
    return get_json(url, params, accept=overpass_complete, timeout=READ_TIMEOUT,
                    max_bytes=LANDCOVER_MAX_BYTES, attempts=1)


def fetch_once(url: str, params: dict[str, Any] | None = None) -> Any:
    """Any other Overpass query this layer makes, on the same terms."""
    return get_json(url, params, accept=overpass_complete, timeout=READ_TIMEOUT, attempts=1)


def _values(key: str) -> str:
    return "|".join(sorted(value for (k, value) in LANDCOVER if k == key))


def landcover_query(south: float, west: float, north: float, east: float,
                    centre: LatLon) -> str:
    """Every mapped area the box touches, and every one the garden lies inside.

    A box query finds an area whose outline crosses the box. One that holds the
    whole box — the residential quarter a garden sits in, a forest around a
    clearing — has no outline there to find, so `is_in` asks which areas hold
    the garden's centre and `pivot` turns them back into their ways and
    relations.
    """
    # Six places is a tenth of a metre, and the box is written eight times.
    box = f"({south:.6f},{west:.6f},{north:.6f},{east:.6f})"
    parts = []
    for key in KEY_ORDER:
        tag = f'["{key}"~"^({_values(key)})$"]'
        parts.append(f"way{tag}{box};relation{tag}{box};"
                     f"way(pivot.here){tag};relation(pivot.here){tag};")
    return (
        f"[out:json][timeout:{QUERY_TIMEOUT_S}];"
        f"is_in({centre.lat:.6f},{centre.lon:.6f})->.here;"
        f"({''.join(parts)});"
        # `body`, the default, and never `tags`: at `tags` Overpass leaves a
        # relation's members out, and with them the geometry the rings are
        # joined from. The one live request (doc 114) came back with a wood as
        # a relation with tags and a bounding box and nothing else.
        f"out geom;"
    )


def landcover_in(
    south: float, west: float, north: float, east: float, *, centre: LatLon,
    fetch: Fetch = fetch_landcover,
) -> list[OsmArea]:
    """The areas around a garden, as rings in degrees.

    As with the streets: a malformed answer is no areas, because the garden has
    to be made; an answer Overpass says it gave up on raises, because "nothing
    here" would be a claim, and a cached one.
    """
    raw = complete_or_fail(fetch(OVERPASS, {"data": landcover_query(
        south, west, north, east, centre)}))
    if not isinstance(raw, dict) or not isinstance(raw.get("elements"), list):
        return []
    found: list[OsmArea] = []
    for element in raw["elements"]:
        area = _area_of(element) if isinstance(element, dict) else None
        if area is not None:
            found.append(area)
    return found


def kind_of(tags: dict[str, str]) -> str | None:
    """The plan's class for these tags, or None for one it does not draw."""
    for key in KEY_ORDER:
        kind = LANDCOVER.get((key, tags.get(key, "")))
        if kind is not None:
            return kind
    return None


def _area_of(element: dict[str, Any]) -> OsmArea | None:
    raw_tags = element.get("tags")
    if not isinstance(raw_tags, dict):
        return None
    tags = {str(k): str(v) for k, v in raw_tags.items()}
    kind = kind_of(tags)
    if kind is None:
        return None
    osm_id = element.get("id")
    osm_id = osm_id if isinstance(osm_id, int) else 0
    if element.get("type") == "way":
        ring = _points(element.get("geometry"))
        if ring is None or len(ring) < 4 or ring[0] != ring[-1]:
            # An area that does not close is a line somebody tagged as one.
            return None
        return OsmArea(osm_id=osm_id, kind=kind, outers=[ring[:-1]], inners=[])
    if element.get("type") == "relation" and tags.get("type") == "multipolygon":
        members = [m for m in element.get("members") or []
                   if isinstance(m, dict) and m.get("type") == "way"]
        outers = assemble([_points(m.get("geometry")) for m in members
                           if m.get("role") in OUTER_ROLES])
        inners = assemble([_points(m.get("geometry")) for m in members
                           if m.get("role") == "inner"])
        # A hole whose outer could not be closed has nothing to be a hole in:
        # kept, it filled as the class, a clearing drawn as wood (review).
        inners = [ring for ring in inners if any(_within(ring, outer) for outer in outers)]
        return OsmArea(osm_id=osm_id, kind=kind, outers=outers, inners=inners) if outers else None
    return None


def _within(ring: list[LatLon], outer: list[LatLon]) -> bool:
    """Whether a ring lies in an outer: any of its edge midpoints strictly
    inside, so a hole touching its outline at a corner still counts."""
    return any(_inside(LatLon(lat=(a.lat + b.lat) / 2, lon=(a.lon + b.lon) / 2), outer)
               for a, b in zip(ring, ring[1:] + ring[:1], strict=True))


def _inside(point: LatLon, ring: list[LatLon]) -> bool:
    inside = False
    for a, b in zip(ring, ring[1:] + ring[:1], strict=True):
        if (a.lat > point.lat) != (b.lat > point.lat):
            crossing = a.lon + (point.lat - a.lat) * (b.lon - a.lon) / (b.lat - a.lat)
            if crossing > point.lon:
                inside = not inside
    return inside


def _points(geometry: Any) -> list[LatLon] | None:
    """A way's nodes, or None if any of them is not a point: a way with a hole
    in its node list would be drawn as a different shape."""
    if not isinstance(geometry, list):
        return None
    ring: list[LatLon] = []
    for point in geometry:
        if not isinstance(point, dict):
            return None
        lat, lon = point.get("lat"), point.get("lon")
        if not (_number(lat) and _number(lon)):
            return None
        ring.append(LatLon(lat=float(lat), lon=float(lon)))
    return ring


def _number(value: object) -> TypeGuard[float]:
    """A coordinate: an int or a float, never a string or a bool."""
    return isinstance(value, int | float) and not isinstance(value, bool)


def assemble(pieces: list[list[LatLon] | None]) -> list[list[LatLon]]:
    """Join ways end to end into closed rings, the last point not repeated.

    A multipolygon's outline is usually several ways, each a stretch of it, in
    no particular order or direction. Drawn one by one they are open lines, and
    a filled open line closes itself with a straight edge — a wedge across the
    plan. So a chain that cannot be closed is dropped, never drawn.
    """
    rings: list[list[LatLon]] = []
    loose: list[list[LatLon]] = []
    for piece in pieces:
        if piece is None or len(piece) < 2:
            continue
        (rings if piece[0] == piece[-1] else loose).append(list(piece))
    while loose:
        ring = loose.pop()
        while ring[0] != ring[-1]:
            joined = _next_piece(ring[-1], loose)
            if joined is None:
                break
            ring.extend(joined[1:])
        if ring[0] == ring[-1]:
            rings.append(ring)
    return [ring[:-1] for ring in rings if len(ring) >= 4]


def _next_piece(end: LatLon, loose: list[list[LatLon]]) -> list[LatLon] | None:
    """The piece that continues from `end`, taken out of `loose` and turned to
    run on from it; None if no piece touches it."""
    for index, piece in enumerate(loose):
        if piece[0] == end:
            return loose.pop(index)
        if piece[-1] == end:
            return list(reversed(loose.pop(index)))
    return None


__all__ = ["KEY_ORDER", "LANDCOVER", "OsmArea", "assemble", "kind_of", "landcover_in",
           "landcover_query"]
