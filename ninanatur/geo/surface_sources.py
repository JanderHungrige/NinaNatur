"""Services that say how tall the things standing on the ground are.

Wave 17 built a registry for terrain. This is its sibling and it answers a
different question: not *where is the ground* but *what is on it, and how far
up*. Same rule — read from each service's own capabilities, confirmed with a
real request, and a state with nothing gets no entry.

Probed on 2026-09-06. **Every one of the eight states with a terrain service has
a surface model too**, which is not a coincidence: they come from the same
airborne laser scanning, and a survey that publishes one usually publishes both.

Two products, and the difference matters more than the names suggest:

- **nDOM** — *normalised*: the surface minus the terrain, already subtracted, so
  a value is the height of a thing above the ground it stands on. Nordrhein-
  Westfalen and Mecklenburg-Vorpommern publish one. NRW's is at **0.5 m**, the
  finest raster in either registry.
- **DOM** — the raw surface, in metres above sea level like the terrain. Usable
  for the same purpose, at the cost of a second request and a subtraction, and
  of the two rasters agreeing about where they are.

A crown, a roof and a parked lorry all look the same to either of them. That is
the limit of this whole family of data and it is why the building footprints
still come from OSM: a surface model says *how tall*, and something else has to
say *what*.
"""
from __future__ import annotations

from dataclasses import dataclass

from ninanatur.geo.terrain_sources import AXES_EN, AXES_XY

#: Already differenced against the terrain: a value is height above ground.
NORMALISED = "ndom"
#: Raw surface, in metres above the height reference, like the terrain.
SURFACE = "dom"


@dataclass(frozen=True)
class SurfaceSource:
    """One state's surface model, as a coverage service."""

    state: str
    url: str
    coverage: str
    epsg: int
    axes: tuple[str, str]
    cell_m: float
    #: `ndom` or `dom`. A caller that wants object heights must subtract the
    #: terrain itself for a `dom`, and must not for an `ndom` — doing it twice
    #: gives negative buildings, which is the failure that looks like a bug in
    #: the shading model rather than in the fetch.
    kind: str
    licence: str
    attribution: str


SURFACE_SOURCES: tuple[SurfaceSource, ...] = (
    SurfaceSource(
        state="Nordrhein-Westfalen",
        url="https://www.wcs.nrw.de/geobasis/wcs_nw_ndom",
        coverage="nw_ndom",
        epsg=25832,
        axes=AXES_XY,
        # Half a metre. Fine enough to see a garden wall, and the only source in
        # either registry that is finer than the DGM1 beside it.
        cell_m=0.5,
        kind=NORMALISED,
        licence="dl-de/zero-2-0",
        attribution="© Geobasis NRW",
    ),
    SurfaceSource(
        state="Mecklenburg-Vorpommern",
        url="https://www.geodaten-mv.de/dienste/ndom_wcs",
        coverage="mv_ndom",
        epsg=25833,
        axes=AXES_XY,
        cell_m=1.0,
        kind=NORMALISED,
        licence="keine Bedingungen, Quellenvermerk verpflichtend",
        attribution="© GeoBasis-DE/M-V",
    ),
    SurfaceSource(
        state="Niedersachsen",
        url="https://opendata.geoservices.lgln.niedersachsen.de/dom_wcs",
        coverage="ni_dom1",
        epsg=25832,
        axes=AXES_XY,
        cell_m=1.0,
        kind=SURFACE,
        licence="CC-BY-4.0",
        attribution="© LGLN, CC BY 4.0",
    ),
    SurfaceSource(
        state="Hessen",
        url="https://inspire-hessen.de/raster/dom1/ows",
        coverage="dom1",
        epsg=25832,
        axes=AXES_EN,
        cell_m=1.0,
        kind=SURFACE,
        licence="dl-de/zero-2-0",
        attribution="© HVBG",
    ),
    SurfaceSource(
        state="Brandenburg",
        url="https://inspire.brandenburg.de/services/el_dom1_wcs",
        coverage="el_elevationgridcoverage",
        epsg=25833,
        # x/y, despite being an INSPIRE service where the others say E/N. The
        # assumption cost a 404 before it was checked.
        axes=AXES_XY,
        cell_m=1.0,
        kind=SURFACE,
        licence="dl-de/by-2-0",
        attribution="© GeoBasis-DE/LGB, dl-de/by-2-0",
    ),
    SurfaceSource(
        state="Berlin",
        url="https://inspire.brandenburg.de/services/el_dom1_wcs",
        coverage="el_elevationgridcoverage",
        epsg=25833,
        axes=AXES_XY,
        cell_m=1.0,
        kind=SURFACE,
        licence="dl-de/by-2-0",
        attribution="© Geoportal Berlin, dl-de/by-2-0; © GeoBasis-DE/LGB, dl-de/by-2-0",
    ),
    SurfaceSource(
        state="Sachsen-Anhalt",
        url=(
            "https://geodatenportal.sachsen-anhalt.de/"
            "ows_INSPIRE_LVermGeo_ATKIS_EL_DOM_WCS"
        ),
        coverage="Coverage1",
        epsg=25832,
        axes=AXES_XY,
        cell_m=1.0,
        kind=SURFACE,
        licence="dl-de/by-2-0",
        attribution="© GeoBasis-DE / LVermGeo LSA, dl-de/by-2-0",
    ),
    SurfaceSource(
        state="Baden-Württemberg",
        url="https://owsproxy.lgl-bw.de/owsproxy/wcs/WCS_INSP_BW_Hoehe_Coverage_DOM5",
        coverage="EL.ElevationGridCoverage",
        epsg=25832,
        axes=AXES_EN,
        # Five metres, not one. Wider than most houses, so it can say a village
        # is built up and cannot say how tall one house is. Recorded rather than
        # dropped, because the caller has to be able to refuse it.
        cell_m=5.0,
        kind=SURFACE,
        licence="dl-de/by-2-0",
        attribution="© LGL-BW, dl-de/by-2-0",
    ),
)

#: Finer than this and a raster cannot say how tall one house is: a 5 m cell is
#: wider than a small dwelling, so its value is a blend of roof and garden.
USABLE_CELL_M = 2.0


def by_state(state: str) -> SurfaceSource | None:
    """The surface model for this Bundesland, or None where there is none."""
    for entry in SURFACE_SOURCES:
        if entry.state.lower() == state.lower():
            return entry
    return None


def measures_buildings(source: SurfaceSource) -> bool:
    """Whether this source is fine enough to measure one building.

    Separate from being in the registry at all: Baden-Württemberg's 5 m coverage
    is real, open and correctly listed, and it still cannot answer the question
    this wave asks.
    """
    return source.cell_m <= USABLE_CELL_M


__all__ = [
    "NORMALISED",
    "SURFACE",
    "SURFACE_SOURCES",
    "USABLE_CELL_M",
    "SurfaceSource",
    "by_state",
    "measures_buildings",
]
