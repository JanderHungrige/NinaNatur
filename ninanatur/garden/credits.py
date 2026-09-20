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
"""
from __future__ import annotations

from dataclasses import dataclass

from ninanatur.garden.models import Garden
from ninanatur.geo.far_horizon import GLO30_SOURCE
from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.geo.terrain_sources import by_state as terrain_service
from ninanatur.geo.tile_sources import (
    COPERNICUS_ATTRIBUTION,
    COPERNICUS_LICENCE,
    ground_tiles_for,
    lod2_tiles_for,
    name_of,
)

#: What a surveyed height means about where it came from (doc 93).
SURVEYED = "survey"


@dataclass(frozen=True)
class Credit:
    """One source a garden's numbers rest on."""

    #: `ground`, `horizon` or `buildings` — what it decided.
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


def credits_for(garden: Garden, *, ground: TerrainWindow | None,
                horizon_source: str | None) -> list[Credit]:
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


__all__ = ["Credit", "LatLon", "credits_for", "tiles_available"]
