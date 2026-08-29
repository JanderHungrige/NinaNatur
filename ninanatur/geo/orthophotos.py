"""State orthophoto services that may actually be used, and their attribution.

Wave 8's feature 0 asked the licence question before anything was built on
imagery — the same rule that kept this project off NaturaDB. The answer, probed
service by service on 2026-08-29:

There is no federal source; the BKG endpoint refuses anonymous requests (403).
Each Bundesland publishes its own, under its own licence, with its own required
attribution string. So this is a registry, not a URL — and a Bundesland that is
not in it is not a gap to paper over with a neighbour's imagery.

Every entry here was read from that service's own GetCapabilities, not from a
summary of it.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Orthophoto:
    """One state's aerial imagery service.

    `attribution` is not decoration: DL-DE/BY-2.0 and CC-BY-4.0 both require the
    named credit, and imagery shown without it is imagery used outside its
    licence.
    """

    state: str
    url: str
    layer: str
    licence: str
    attribution: str


ORTHOPHOTOS: tuple[Orthophoto, ...] = (
    Orthophoto(
        state="Nordrhein-Westfalen",
        url="https://www.wms.nrw.de/geobasis/wms_nw_dop",
        layer="nw_dop_rgb",
        licence="Open Data (GovData / VermKatG NRW)",
        attribution="© Geobasis NRW",
    ),
    Orthophoto(
        state="Brandenburg",
        url="https://isk.geobasis-bb.de/mapproxy/dop20c/service/wms",
        layer="bebb_dop20c",
        licence="dl-de/by-2-0",
        attribution="© GeoBasis-DE/LGB, dl-de/by-2-0",
    ),
    Orthophoto(
        state="Thüringen",
        url="https://www.geoproxy.geoportal-th.de/geoproxy/services/DOP",
        layer="th_dop200rgb",
        licence="dl-de/by-2-0",
        attribution="© GDI-Th, dl-de/by-2-0",
    ),
    Orthophoto(
        state="Sachsen",
        url="https://geodienste.sachsen.de/wms_geosn_dop-rgb/guest",
        layer="sn_dop_020",
        licence="kostenfrei, Nutzungsbedingungen Geoportal Sachsen",
        attribution="© GeoSN",
    ),
    Orthophoto(
        state="Niedersachsen",
        url="https://opendata.lgln.niedersachsen.de/doorman/noauth/dop_wms",
        layer="ni_dop20",
        licence="CC-BY-4.0",
        attribution="© LGLN",
    ),
    Orthophoto(
        state="Baden-Württemberg",
        url="https://owsproxy.lgl-bw.de/owsproxy/ows/WMS_LGL-BW_ATKIS_DOP_20_C",
        layer="IMAGES_DOP_20_RGB",
        licence="dl-de/by-2-0",
        attribution="© LGL-BW, dl-de/by-2-0",
    ),
    Orthophoto(
        state="Bayern",
        url="https://geoservices.bayern.de/od/wms/dop/v1/dop40",
        layer="by_dop40c",
        licence="CC-BY-4.0",
        attribution="© Bayerische Vermessungsverwaltung",
    ),
    Orthophoto(
        state="Schleswig-Holstein",
        url="https://dienste.gdi-sh.de/WMS_SH_DOP20col_OpenGBD",
        layer="sh_dop20_rgb",
        licence="keine Beschränkungen (Open GBD)",
        attribution="© GeoBasis-DE/LVermGeo SH",
    ),
)


def by_state(state: str) -> Orthophoto | None:
    for entry in ORTHOPHOTOS:
        if entry.state.lower() == state.lower():
            return entry
    return None
