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


#: Schleswig-Holstein serves every product from one script, and the query
#: carries the tile's **ten-kilometre block** beside the file name. `id` is
#: fixed per product; `live` is the survey year, which for the terrain model
#: differs tile by tile and is therefore read out of the name the index gave.
SH_DOWNLOAD = ("https://geodaten.schleswig-holstein.de/gaialight-sh/_apps/"
               "dladownload/massen.php")


def sh_block(east_km: int, north_km: int) -> str:
    """The ten-kilometre block a tile sits in, as the query spells it."""
    return f"32{east_km // 10 * 10}_{north_km // 10 * 10}"


def sh_named(product_id: int, year: str = "") -> Callable[[str, tuple[int, int]], str]:
    """The address for a name Schleswig-Holstein's own index gave us.

    `year` empty means take it from the name, which is where the terrain
    model's lives; the building model has no year in its name and a fixed one
    in its query.
    """
    def address(name: str, corner: tuple[int, int]) -> str:
        live = year or name.rsplit("_", 1)[-1].split(".")[0]
        return (f"{SH_DOWNLOAD}?file={name}&id={product_id}"
                f"&live={live}&km={sh_block(*corner)}")
    return address


def sh_lod2(east_km: int, north_km: int) -> str:
    """Its building model carries no year, so this one is arithmetic."""
    return f"LoD2_32_{east_km}_{north_km}_1_SH"


#: Bremen publishes its city and Bremerhaven as separate archives, and the two
#: disagree: Bremerhaven's terrain model has a **double** underscore after the
#: easting, its surface model a single one. Both are read out of the archive's
#: own directory, so this records the shape rather than building it.
BREMEN_DOWNLOAD = "https://gdi2.geo.bremen.de/inspire/download/"


def bremen(folder: str, *names: str) -> tuple[str, ...]:
    """The city's archive and Bremerhaven's, for one product."""
    return tuple(f"{BREMEN_DOWNLOAD}{folder}/data/{name}" for name in names)
