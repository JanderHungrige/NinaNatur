"""Address search and building outlines from OpenStreetMap.

Streets are in `osm_streets.py`; the Overpass fetch both use is here.

Both Nominatim and Overpass are free services run for the community, and this
project is a guest on them. Requests go through the ingest HTTP layer — cached
on disk, delayed, retried — and carry a User-Agent that says who is calling,
which their usage policies require and which is also simply how one behaves on
somebody else's infrastructure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ninanatur.geo.projection import LatLon
from ninanatur.geo.surroundings import OsmBuilding
from ninanatur.ingest.http import HttpError, get_json

NOMINATIM = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
OVERPASS = "https://overpass-api.de/api/interpreter"

# Germany only, matching the catalogue. A search that happily finds Ohio would
# produce a garden this product has no plants for.
COUNTRY_CODES = "de"


@dataclass(frozen=True)
class Place:
    name: str
    lat: float
    lon: float


class Fetch(Protocol):
    def __call__(self, url: str, params: dict[str, Any] | None = None) -> Any: ...


def search_address(query: str, *, fetch: Fetch = get_json, limit: int = 5) -> list[Place]:
    """Addresses matching a query, most relevant first."""
    if not query.strip():
        return []
    raw = fetch(
        NOMINATIM,
        {
            "q": query.strip(),
            "format": "json",
            "limit": str(limit),
            "countrycodes": COUNTRY_CODES,
            "addressdetails": "0",
        },
    )
    if not isinstance(raw, list):
        return []
    return [
        Place(name=str(item["display_name"]), lat=float(item["lat"]), lon=float(item["lon"]))
        for item in raw
        if "display_name" in item and "lat" in item and "lon" in item
    ]


def overpass_complete(raw: Any) -> bool:
    """Whether Overpass finished the query it was asked.

    When it gives up — out of time, out of memory — it still answers HTTP 200,
    with whatever elements it had and a `remark` saying `runtime error`. Taken
    at its word that is "no buildings here", and cached it stayed that way for
    good. It is a failure to fetch, and is reported as one.
    """
    if not isinstance(raw, dict):
        return True  # malformed is handled where it is read; this asks one thing
    return "runtime error" not in str(raw.get("remark") or "")


def fetch_overpass(url: str, params: dict[str, Any] | None = None) -> Any:
    """The live fetch: an incomplete answer is refused before it can be cached."""
    return get_json(url, params, accept=overpass_complete)


def complete_or_fail(raw: Any) -> Any:
    """The same refusal for an answer that came through a fetch of its own."""
    if not overpass_complete(raw):
        raise HttpError(f"Overpass gave up on the query: {raw.get('remark')}")
    return raw


def _overpass_query(south: float, west: float, north: float, east: float) -> str:
    # `out center` gives one point per element without the node list, which is a
    # fraction of the payload and all the shading model needs.
    #
    # Ways *and* relations. A building drawn as a multipolygon — a courtyard, a
    # farm range, anything with a hole in it — is a relation, and asking only
    # for ways dropped it without a word. On a farmyard that is most of the
    # buildings somebody can plainly see on the map.
    return (
        f"[out:json][timeout:40];"
        f"("
        f'way["building"]({south},{west},{north},{east});'
        f'relation["building"]({south},{west},{north},{east});'
        f");"
        # `geom`, not `center`. A centre alone says nothing about size, so every
        # building was judged for shading — and drawn — as the same 9 m square,
        # a 60 m barn included. Overpass answers one or the other, never both,
        # which is why the centre is computed below.
        f"out tags geom;"
    )


def buildings_in(
    south: float, west: float, north: float, east: float, *, fetch: Fetch = fetch_overpass
) -> list[OsmBuilding]:
    """Buildings whose centre lies in the box."""
    raw = complete_or_fail(fetch(OVERPASS, {"data": _overpass_query(south, west, north, east)}))
    if not isinstance(raw, dict):
        return []
    found: list[OsmBuilding] = []
    for element in raw.get("elements", []):
        outline = _outline_of(element)
        centre = _centre_of(element, outline)
        # Neither an outline nor a centre is nothing to place. A relation whose
        # members were not returned lands here, which is why it is skipped
        # rather than defaulted to somewhere.
        if centre is None:
            continue
        found.append(
            OsmBuilding(
                osm_id=int(element.get("id", 0)),
                centre=centre,
                outline=outline,
                tags={str(k): str(v) for k, v in (element.get("tags") or {}).items()},
            )
        )
    return found


def _outline_of(element: dict[str, Any]) -> list[LatLon]:
    """The node list, from a way's own geometry or a relation's members."""
    geometry = element.get("geometry")
    if isinstance(geometry, list):
        return [
            LatLon(lat=float(p["lat"]), lon=float(p["lon"]))
            for p in geometry
            if isinstance(p, dict) and "lat" in p and "lon" in p
        ]
    # Outer rings only. A multipolygon's members are outer rings *and* holes,
    # and concatenating them gives a shape spanning both — which is how a
    # courtyard building came out enormous. One outer ring is enough for a
    # shadow; the second is rare and the hole is not a wall.
    for member in element.get("members") or []:
        if not isinstance(member, dict) or member.get("role") != "outer":
            continue
        ring = [
            LatLon(lat=float(p["lat"]), lon=float(p["lon"]))
            for p in member.get("geometry") or []
            if isinstance(p, dict) and "lat" in p and "lon" in p
        ]
        if len(ring) >= 3:
            return ring
    return []


def _centre_of(element: dict[str, Any], outline: list[LatLon]) -> LatLon | None:
    """Where the building is. From `center` when Overpass sent one, otherwise
    the mean of the outline — `out geom` returns one or the other, never both."""
    centre = element.get("center")
    if isinstance(centre, dict) and "lat" in centre and "lon" in centre:
        return LatLon(lat=float(centre["lat"]), lon=float(centre["lon"]))
    if not outline:
        return None
    return LatLon(
        lat=sum(p.lat for p in outline) / len(outline),
        lon=sum(p.lon for p in outline) / len(outline),
    )


#: ISO 3166-2 codes for the sixteen Bundesländer.
#:
#: Needed because Nominatim reports a `state` for thirteen of them and **not for
#: the three city-states**: a point in Berlin comes back with `city: Berlin` and
#: `ISO3166-2-lvl4: DE-BE`, and no `state` at all. That blind spot has been here
#: since Wave 8 and only showed up when Berlin got a terrain service — Wave 8's
#: registry happens to have no entry for any city-state, so nothing failed
#: visibly.
#:
#: The code is the better key anyway: it is unambiguous, and it does not depend
#: on which spelling Nominatim returns this year.
ISO_STATES: dict[str, str] = {
    "DE-BW": "Baden-Württemberg",
    "DE-BY": "Bayern",
    "DE-BE": "Berlin",
    "DE-BB": "Brandenburg",
    "DE-HB": "Bremen",
    "DE-HH": "Hamburg",
    "DE-HE": "Hessen",
    "DE-MV": "Mecklenburg-Vorpommern",
    "DE-NI": "Niedersachsen",
    "DE-NW": "Nordrhein-Westfalen",
    "DE-RP": "Rheinland-Pfalz",
    "DE-SL": "Saarland",
    "DE-SN": "Sachsen",
    "DE-ST": "Sachsen-Anhalt",
    "DE-SH": "Schleswig-Holstein",
    "DE-TH": "Thüringen",
}


def state_at(lat: float, lon: float, *, fetch: Fetch = get_json) -> str | None:
    """Which Bundesland a point is in, or None.

    Needed because orthophoto and terrain services are per state, each with its
    own licence and required credit. A point whose state cannot be determined
    gets neither rather than a neighbour's — using one state's data over
    another's ground is using it outside its licence area.
    """
    raw = fetch(
        NOMINATIM_REVERSE,
        {"lat": f"{lat:.5f}", "lon": f"{lon:.5f}", "format": "json",
         "zoom": "8", "addressdetails": "1"},
    )
    if not isinstance(raw, dict):
        return None
    address = raw.get("address")
    if not isinstance(address, dict):
        return None
    state = address.get("state")
    if state:
        return str(state)
    # A city-state. The ISO code is the only field that names it.
    iso = address.get("ISO3166-2-lvl4")
    return ISO_STATES.get(str(iso)) if iso else None
