"""State elevation services that may actually be used, and their attribution.

Wave 8 asked the licence question before anything was built on imagery, and
`orthophotos.py` is the answer that came out. This is the same question asked of
terrain, and it produced the same shape of answer: a registry, not a URL.

Probed service by service on 2026-09-05, every entry read from that service's
own `GetCapabilities` and confirmed with a real 200 m `GetCoverage`. Six states
answer, and the rest are absent rather than approximated.

**Saarland is the reason this is a registry.** Its service answers, its metadata
is listed as open by every aggregator — and its own `AccessConstraints` say
"Jegliche andere Nutzung, so auch das Einbinden in weitere Anwendungen
(Download) ist kostenpflichtig". Viewing it in the state's own portal is free;
using it here is not. It is therefore not here. The coverage it serves is also
5 m rather than the DGM1 its title claims.

Not found, and so not included — a bbox coverage service could not be reached
for: Bayern, Berlin, Bremen, Hamburg, Rheinland-Pfalz, Sachsen, Sachsen-Anhalt,
Schleswig-Holstein, Thüringen. Several publish DGM1 as open data by download or
as a WMS; Thüringen's `.../services/DGM` answers a WCS request with WMS
capabilities, and Sachsen and Sachsen-Anhalt return 403 to anonymous requests.
The federal `sgx.geodatenzentrum.de/wcs_dgm1` also returns 403, exactly as the
BKG orthophoto endpoint did in Wave 8. A gap here is a gap, and the model says
so rather than borrowing a neighbour's ground.
"""
from __future__ import annotations

from dataclasses import dataclass

#: What a service calls its two axes in a `SUBSET`. The state services say
#: `x`/`y`; the INSPIRE ones say `E`/`N`. Getting it wrong is not an error
#: message — it is a 404, which is how this was found.
AXES_XY: tuple[str, str] = ("x", "y")
AXES_EN: tuple[str, str] = ("E", "N")


@dataclass(frozen=True)
class TerrainSource:
    """One state's digital terrain model, as a coverage service.

    `attribution` is not decoration: dl-de/by-2-0 and CC-BY-4.0 both require the
    named credit, and a height shown without it is a height used outside its
    licence. Only dl-de/zero-2-0 asks for nothing, and it is given anyway.
    """

    state: str
    url: str
    coverage: str
    #: ETRS89/UTM zone 32 (25832) or 33 (25833). Both appear; a request in the
    #: wrong one lands in the sea off Norway rather than failing.
    epsg: int
    axes: tuple[str, str]
    #: Ground resolution of the coverage, in metres.
    cell_m: float
    #: How finely the height itself is quantised. The DGM1 specification says
    #: 0.01 m — but Baden-Württemberg's INSPIRE coverage delivers 16-bit whole
    #: metres, and a 20 m garden on a 3 % slope rises 0.6 m, which whole metres
    #: cannot see. Recorded so the page can say so rather than imply precision.
    vertical_step_m: float
    licence: str
    attribution: str


TERRAIN_SOURCES: tuple[TerrainSource, ...] = (
    TerrainSource(
        state="Nordrhein-Westfalen",
        url="https://www.wcs.nrw.de/geobasis/wcs_nw_dgm",
        coverage="nw_dgm",
        epsg=25832,
        axes=AXES_XY,
        cell_m=1.0,
        vertical_step_m=0.01,
        licence="dl-de/zero-2-0",
        attribution="© Geobasis NRW",
    ),
    TerrainSource(
        state="Brandenburg",
        url="https://isk.geobasis-bb.de/ows/dgm_wcs",
        coverage="bb_dgm",
        epsg=25833,
        axes=AXES_XY,
        cell_m=1.0,
        vertical_step_m=0.01,
        licence="dl-de/by-2-0",
        # The service's own note: Berlin data carried in this coverage needs the
        # second credit as well, so it is given unconditionally rather than
        # worked out per request.
        attribution="© GeoBasis-DE/LGB, dl-de/by-2-0; © Geoportal Berlin, dl-de/by-2-0",
    ),
    TerrainSource(
        state="Niedersachsen",
        url="https://opendata.geoservices.lgln.niedersachsen.de/dgm_wcs",
        coverage="ni_dgm1",
        epsg=25832,
        axes=AXES_XY,
        cell_m=1.0,
        vertical_step_m=0.01,
        licence="CC-BY-4.0",
        attribution="© LGLN, CC BY 4.0",
    ),
    TerrainSource(
        state="Mecklenburg-Vorpommern",
        url="https://www.geodaten-mv.de/dienste/dgm_wcs",
        coverage="mv_dgm",
        epsg=25833,
        axes=AXES_XY,
        cell_m=1.0,
        vertical_step_m=0.01,
        licence="keine Bedingungen, Quellenvermerk verpflichtend",
        attribution="© GeoBasis-DE/M-V",
    ),
    TerrainSource(
        state="Hessen",
        url="https://inspire-hessen.de/raster/dgm1/ows",
        coverage="he_dgm1",
        epsg=25832,
        axes=AXES_EN,
        cell_m=1.0,
        vertical_step_m=0.01,
        licence="dl-de/zero-2-0",
        attribution="© HVBG",
    ),
    TerrainSource(
        state="Baden-Württemberg",
        url="https://owsproxy.lgl-bw.de/owsproxy/wcs/WCS_INSP_BW_Hoehe_Coverage_DGM1",
        coverage="EL.ElevationGridCoverage",
        epsg=25832,
        axes=AXES_EN,
        cell_m=1.0,
        # Whole metres, and big-endian 16-bit unsigned into the bargain. Both
        # verified against Stuttgart, where the values read 241-244 m.
        vertical_step_m=1.0,
        licence="dl-de/by-2-0",
        attribution="© LGL-BW, dl-de/by-2-0",
    ),
)


def by_state(state: str) -> TerrainSource | None:
    """The service for this Bundesland, or None where there is none.

    None is an answer rather than a failure, and the caller has to treat it as
    one: a garden in a state with no service keeps the flat assumption and is
    told so.
    """
    for entry in TERRAIN_SOURCES:
        if entry.state.lower() == state.lower():
            return entry
    return None


__all__ = ["AXES_EN", "AXES_XY", "TERRAIN_SOURCES", "TerrainSource", "by_state"]
