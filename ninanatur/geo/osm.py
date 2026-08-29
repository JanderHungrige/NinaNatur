"""Address search and building outlines from OpenStreetMap.

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
from ninanatur.ingest.http import get_json

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


def _overpass_query(south: float, west: float, north: float, east: float) -> str:
    # `out center` gives one point per way without the node list, which is a
    # fraction of the payload and all the shading model needs.
    return (
        f"[out:json][timeout:40];"
        f'way["building"]({south},{west},{north},{east});'
        f"out tags center;"
    )


def buildings_in(
    south: float, west: float, north: float, east: float, *, fetch: Fetch = get_json
) -> list[OsmBuilding]:
    """Buildings whose centre lies in the box."""
    raw = fetch(OVERPASS, {"data": _overpass_query(south, west, north, east)})
    if not isinstance(raw, dict):
        return []
    found: list[OsmBuilding] = []
    for element in raw.get("elements", []):
        centre = element.get("center")
        if centre is None:
            continue
        found.append(
            OsmBuilding(
                osm_id=int(element.get("id", 0)),
                centre=LatLon(lat=float(centre["lat"]), lon=float(centre["lon"])),
                outline=[],
                tags={str(k): str(v) for k, v in (element.get("tags") or {}).items()},
            )
        )
    return found


def state_at(lat: float, lon: float, *, fetch: Fetch = get_json) -> str | None:
    """Which Bundesland a point is in, or None.

    Needed because orthophoto services are per state, each with its own licence
    and required credit. A point whose state cannot be determined gets no
    imagery rather than a neighbour's — using one state's imagery over another's
    ground is using it outside its licence area.
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
    return str(state) if state else None
