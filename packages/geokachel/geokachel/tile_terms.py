"""What each state's licence asks for — Wave 25, doc 102.

A state's licence, the credit it requires and the UTM zone its tiles are
numbered in belong to the **state**, not to each product it publishes. Written
out per product they drift: Bayern's laser carried a credit one word different
from its ground until they were put in one place.

Every string here was read from that state's own terms page on 2026-09-20. A
credit is a licence obligation — a height shown without it is a height used
outside its licence — so these are quoted as the state writes them, not tidied.
"""
from __future__ import annotations

from typing import TypedDict


class _Terms(TypedDict):
    """What every product of one state has in common."""

    state: str
    licence: str
    attribution: str
    epsg: int


#: Licence, credit and zone per state, each read from that state's own terms
#: page on 2026-09-20. Zone 25832 is UTM32 and 25833 UTM33; a state east of
#: 12°E that is given the wrong one fetches a tile four hundred kilometres away.
TERMS: dict[str, tuple[str, str, int]] = {
    # The "Datenquelle:" prefix is how Bayern's own tiles write it, in the
    # comment at the head of every CityGML document it publishes.
    "BY": ("CC-BY-4.0",
           "Datenquelle: Bayerische Vermessungsverwaltung – www.geodaten.bayern.de", 25832),
    "NW": ("dl-de/zero-2-0",
           "Land NRW (2026), Datenlizenz Deutschland – Zero – Version 2.0", 25832),
    "NI": ("CC-BY-4.0", "© GeoBasis-DE/LGLN (2026)", 25832),
    "TH": ("dl-de/by-2-0",
           "© GDI-Th (2026), Datenlizenz Deutschland – Namensnennung – Version 2.0", 25832),
    "SN": ("dl-de/by-2-0", "Quelle: GeoSN, dl-de/by-2-0", 25833),
    "BB": ("dl-de/by-2-0", "© GeoBasis-DE/LGB, dl-de/by-2-0", 25833),
    # Zero asks for nothing; the courtesy credit is given anyway.
    "BE": ("dl-de/zero-2-0",
           "Geoportal Berlin, Datenlizenz Deutschland – Zero – Version 2.0", 25833),
    "MV": ("CC-BY-4.0", "© GeoBasis-DE/M-V (2026)", 25833),
    "BW": ("dl-de/by-2-0", "Datenquelle: LGL, www.lgl-bw.de, dl-de/by-2-0", 25832),
    "SL": ("dl-de/by-2-0", "© GeoBasis DE/LVGL-SL (2026)", 25832),
    "HH": ("dl-de/by-2-0", "Quellenvermerk: Freie und Hansestadt Hamburg, "
           "Landesbetrieb Geoinformation und Vermessung (LGV)", 25832),
    "SH": ("CC-BY-4.0", "©GeoBasis-DE/LVermGeo SH/CC BY 4.0", 25832),
    "HB": ("CC-BY-4.0",
           "© GeoBasis-DE / Landesamt GeoInformation Bremen (2026)", 25832),
    "RP": ("dl-de/by-2-0",
           "©GeoBasis-DE / LVermGeoRP (2026), dl-de/by-2-0, www.lvermgeo.rlp.de", 25832),
}


def terms(state: str) -> _Terms:
    """That state's licence, credit and zone, to splat into an entry."""
    licence, attribution, epsg = TERMS[state]
    return {"state": state, "licence": licence, "attribution": attribution, "epsg": epsg}
