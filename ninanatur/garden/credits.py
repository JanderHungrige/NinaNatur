"""Which source said so — Wave 25, feature 7 (doc 106).

A garden's numbers come from as many as three surveys now, and every one of
them asks for something in return: CC-BY-4.0 and dl-de/by-2-0 require the named
credit, the Copernicus terms require theirs, and dl-de/zero-2-0 requires
nothing and is given it anyway.

Until Wave 25 there was one credit to show and `TerrainOut` carried it. Then a
Bavarian garden gained ground from a tile, a horizon from Copernicus and its
roofs from LoD2 — three sources, three licences, one page. This is that list,
built from what a garden actually used rather than from what its state could
in principle offer.

**A credit is not a caption.** A height shown without it is a height used
outside its licence, which is the one thing this project cannot do quietly.

OpenStreetMap joined the list on 2026-09-21 (owner's check, #10): a garden
made from the map draws its streets and its houses' outlines, and ODbL asks
for the credit wherever they are shown.
"""
from __future__ import annotations

from dataclasses import dataclass

from geokachel.terrain_sources import by_state as terrain_service
from geokachel.tile_sources import (
    COPERNICUS_ATTRIBUTION,
    COPERNICUS_LICENCE,
    ground_tiles_for,
    laser_tiles_for,
    lod2_tiles_for,
    name_of,
)

from ninanatur.garden.models import Element, Garden
from ninanatur.garden.objects import ROOFED, ObjectKind
from ninanatur.geo.far_horizon import GLO30_SOURCE
from ninanatur.geo.projection import LatLon
from ninanatur.geo.surroundings import HeightSource
from ninanatur.geo.terrain import TerrainWindow

#: What a surveyed height means about where it came from (doc 93): the value
#: the survey writes. It was the literal "survey", which nothing writes, so the
#: building model was never credited for the houses it measured.
SURVEYED = HeightSource.SURVEYED.value

#: OpenStreetMap's licence, and its credit in the words the map picker uses.
OSM_LICENCE = "ODbL-1.0"
OSM_ATTRIBUTION = "© OpenStreetMap-Mitwirkende"

_BUILDINGS = frozenset(kind.value for kind in ROOFED)


@dataclass(frozen=True)
class Credit:
    """One source a garden's numbers rest on."""

    #: `ground`, `horizon`, `buildings`, `laser` or `map` — what it decided.
    about: str
    #: What it is called on the page: "DGM1 Bayern", "Copernicus GLO-30".
    name: str
    licence: str
    attribution: str
    #: How fine it is, in the source's own terms — "1 m, ±0,01 m", "30 m".
    detail: str | None = None


def _ground_credit(ground: TerrainWindow) -> Credit:
    """The window says its own source; the registry says nothing it does not."""
    return Credit(about="ground", name=f"Geländemodell {name_of(ground.source)}",
                  licence=ground.licence, attribution=ground.attribution,
                  detail=f"{ground.cell_m:g} m, ±{ground.vertical_step_m:g} m")


def _horizon_credit(whose: str) -> Credit | None:
    """A ring from a state's service, or from Copernicus (doc 104)."""
    if whose == GLO30_SOURCE:
        return Credit(about="horizon", name=GLO30_SOURCE, licence=COPERNICUS_LICENCE,
                      attribution=COPERNICUS_ATTRIBUTION, detail="30 m")
    service = terrain_service(name_of(whose))
    if service is None:
        return None
    return Credit(about="horizon", name=f"Horizont {service.state}",
                  licence=service.licence, attribution=service.attribution)


def _buildings_credit(state: str | None) -> Credit | None:
    """The 3D building model, where the state publishes one (doc 105)."""
    source = lod2_tiles_for(state) if state else None
    if source is None:
        return None
    return Credit(about="buildings", name=f"LoD2 {name_of(source.state)}",
                  licence=source.licence,
                  attribution=source.attribution, detail="Höhe ±1 m, Dachform vermessen")


def _laser_credit(whose: str | None) -> Credit | None:
    """The point cloud, where one has been read (doc 107)."""
    if whose is None:
        return None
    source = laser_tiles_for(whose)
    if source is None:
        return None
    density = "" if source.points_per_m2 is None else f"{source.points_per_m2:g} Punkte/m²"
    return Credit(about="laser", name=f"Laserscan {name_of(source.state)}",
                  licence=source.licence, attribution=source.attribution,
                  detail=density or None)


def from_the_map(element: Element) -> bool:
    """Whether this element's shape is OpenStreetMap's (what `garden_from_map` imports).

    Nothing records where an outline came from, so this reads what the import
    leaves behind: a street, or a building whose height, roof or eaves were not
    the gardener's. A house drawn by hand starts as the gardener's in all three
    and no survey measures it (`measured` skips those), so any other source
    means the map brought it — and a later survey replaces its height and roof,
    never its outline. A street drawn by hand is credited too: the one mistake
    this can make is thanking OpenStreetMap once too often. The page asks the
    same question of the same fields (`PlanCredit.tsx`).
    """
    if element.kind == ObjectKind.STREET.value:
        return True
    if element.kind not in _BUILDINGS:
        return False
    return (element.height_source != HeightSource.USER.value
            or element.roof_source == "osm"
            or element.eaves_source == "osm_levels")


def _osm_credit(garden: Garden) -> Credit | None:
    """OpenStreetMap, wherever the plan draws its streets or houses.

    ODbL 1.0 asks for the credit where a work made from its data is shown, and
    the plan is such a work from the moment a garden is made from the map.
    """
    if not any(from_the_map(element) for element in garden.obstacles):
        return None
    return Credit(about="map", name="OpenStreetMap", licence=OSM_LICENCE,
                  attribution=OSM_ATTRIBUTION)


def credits_for(garden: Garden, *, ground: TerrainWindow | None,
                horizon_source: str | None, laser_source: str | None = None) -> list[Credit]:
    """Every source this garden's numbers actually rest on, once each.

    Built from what is stored and nothing else. Naming the building model needs
    a state, and the stored window already says which one measured the ground —
    `by_state` and the tile registry both answer to a key or a name. Looking the
    state up instead would put a reverse geocode on a page load, which is a
    request Nominatim does not need to serve for a caption.
    """
    found: list[Credit] = []
    if ground is not None:
        found.append(_ground_credit(ground))
    if horizon_source is not None:
        ring = _horizon_credit(horizon_source)
        if ring is not None:
            found.append(ring)
    # Only if something in this garden was actually measured by it.
    if ground is not None and any(e.height_source == SURVEYED for e in garden.obstacles):
        building = _buildings_credit(ground.source)
        if building is not None:
            found.append(building)
    laser = _laser_credit(laser_source)
    if laser is not None:
        found.append(laser)
    osm = _osm_credit(garden)
    if osm is not None:
        found.append(osm)
    return _without_repeats(found)


def _without_repeats(credits: list[Credit]) -> list[Credit]:
    """One line per licence and attribution: a state that gave both the ground
    and the ring is thanked once, for both."""
    seen: dict[tuple[str, str], Credit] = {}
    for credit in credits:
        key = (credit.licence, credit.attribution)
        if key in seen:
            first = seen[key]
            seen[key] = Credit(about=f"{first.about}, {credit.about}", name=first.name,
                               licence=first.licence, attribution=first.attribution,
                               detail=first.detail)
        else:
            seen[key] = credit
    return list(seen.values())


def tiles_available(state: str | None) -> bool:
    """Whether this state has ground as tiles — what doc 103 added and what a
    garden computed before it may not know about yet."""
    return state is not None and ground_tiles_for(state) is not None


__all__ = ["Credit", "LatLon", "credits_for", "from_the_map", "tiles_available"]
