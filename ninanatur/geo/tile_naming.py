"""How each state spells a tile — Wave 25, doc 102.

Sixteen surveying offices, sixteen opinions about where the UTM zone goes and
what a product is called. None of it is arbitrary — every one of these names is
the grid written down — so each is a small function here rather than a string
repeated in every entry that uses it.

The disagreements worth knowing: Bayern writes the two kilometre numbers alone
for most products and glues the zone onto the easting for its surface model;
Sachsen and Brandenburg glue it on always; everyone else follows AdV and gives
the zone its own field. Brandenburg puts a hyphen where the rest put an
underscore, and Berlin leaves the zone out of the archive's name entirely.
"""
from __future__ import annotations

from collections.abc import Callable


def bayern_url(product: str, extension: str) -> Callable[[int, int], str]:
    return lambda e, n: f"https://download1.bayernwolke.de/a/{product}/{e}_{n}.{extension}"


#: Bayern: the tile is simply the two kilometre numbers.
def bayern_name(east_km: int, north_km: int) -> str:
    return f"{east_km}_{north_km}"


#: Bayern's surface model writes the zone in front of the easting and the
#: product behind: `32690_5334_20_DOM.tif` is UTM32, 690 km east, 20 cm.
def bayern_dom_name(east_km: int, north_km: int) -> str:
    return f"32{east_km}_{north_km}_20_DOM"


#: What most states write, and what AdV's own scheme looks like: a product
#: prefix, the UTM zone as its own field, the two kilometre numbers of the
#: south-west corner, how many kilometres across, and the state. Nordrhein-
#: Westfalen, Rheinland-Pfalz, Niedersachsen, Thüringen and Baden-Württemberg
#: all use it; the disagreements are capitalisation and the sheet size.
def adv_name(prefix: str, east_km: int, north_km: int, *, zone: int = 32,
              km: int = 1, suffix: str) -> str:
    return f"{prefix}_{zone}_{east_km}_{north_km}_{km}_{suffix}"


def nrw_name(east_km: int, north_km: int, prefix: str, suffix: str) -> str:
    return adv_name(prefix, east_km, north_km, suffix=suffix)


#: Thüringen: the AdV name with the survey period on the end, all of it zipped.
def th_url(folder: str) -> Callable[[int, int], str]:
    return lambda e, n: (f"https://geoportal.geoportal-th.de/hoehendaten/{folder}/"
                         f"{th_name(folder.split('/')[0].lower())(e, n)}.zip")


def th_name(product: str) -> Callable[[int, int], str]:
    return lambda e, n: adv_name(f"{product}1" if product != "las" else "las",
                                  e, n, suffix="th_2020-2025")


#: Sachsen glues the zone to the easting, works in two-kilometre tiles, and
#: hands every product out of a share whose token is fixed per product.
def sn_name(product: str, kind: str) -> Callable[[int, int], str]:
    return lambda e, n: f"{product}_33{e}_{n}_2_sn_{kind}"


def sn_url(product: str, kind: str, token: str) -> Callable[[int, int], str]:
    return lambda e, n: ("https://geocloud.landesvermessung.sachsen.de/public.php/dav/files/"
                         f"{token}/{sn_name(product, kind)(e, n)}.zip")


#: Brandenburg: the zone glued to the easting and a hyphen before the northing.
def bb_name(product: str) -> Callable[[int, int], str]:
    return lambda e, n: f"{product}_33{e}-{n}"


def bb_url(folder: str, product: str) -> Callable[[int, int], str]:
    return lambda e, n: (f"https://data.geobasis-bb.de/geobasis/daten/{folder}/"
                         f"{bb_name(product)(e, n)}.zip")


#: Saarland publishes no tile: six archives per product, one per Landkreis,
#: each holding its district's tiles. Every one of the twenty-four answered on
#: 2026-09-20. The share token is the state's, and it could be rotated.
SAARLAND_SHARE = ("https://www.shop.lvgl.saarland.de/cloud/public.php/dav/files/"
                  "NK8ndP55qAqGEZD/")
DISTRICTS = ("MZG", "NK", "SB", "SLS", "SPK", "WND")


def saarland(folder: str, pattern: str) -> tuple[str, ...]:
    """Every district's archive of one product."""
    return tuple(f"{SAARLAND_SHARE}{folder}/{pattern.format(lk=lk)}" for lk in DISTRICTS)
