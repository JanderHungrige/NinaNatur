"""The tile registry's own rules — Wave 25, feature 0 (doc 102).

Doc 68's three questions asked of files rather than services: may we use it,
does it say whose it is, and does the address we compute match the address the
state publishes. Nothing here touches the network — that is
`scripts/probe_tile_sources.py`, run deliberately, with its date in the doc.
"""
from __future__ import annotations

import re

import pytest

from ninanatur.geo.tile_sources import (
    FREE_LICENCES,
    TILE_SOURCES,
    TileProduct,
    glo30_url,
    sources_for,
    tile_of,
)


def test_every_entry_may_actually_be_used() -> None:
    """Doc 68's rule, and the reason Saarland's coverage service is absent from
    that registry: a licence that charges for this use is not an entry."""
    for source in TILE_SOURCES:
        assert source.licence in FREE_LICENCES, f"{source.name}: {source.licence}"


def test_every_entry_says_whose_it_is() -> None:
    """dl-de/by-2-0 and CC-BY-4.0 both require the named credit. A height shown
    without it is a height used outside its licence."""
    for source in TILE_SOURCES:
        assert source.attribution.strip(), source.name
        assert len(source.attribution) > 10, f"{source.name}: {source.attribution!r}"


def test_the_address_is_built_from_two_numbers_and_nothing_else() -> None:
    """Every scheme in this family is the grid written down, so a tile's URL is
    arithmetic. Nothing user-typed reaches a path."""
    for source in TILE_SOURCES:
        url = source.url_for(347, 5647)
        assert url.startswith("https://"), source.name
        assert "347" in url or "0347" in url, f"{source.name}: {url}"
        assert "5647" in url, f"{source.name}: {url}"


def test_the_tile_name_round_trips_for_every_state_scheme() -> None:
    """Bayern writes `690_5334`, NRW `LoD2_32_347_5647_1_NW`: the same two
    numbers, differently dressed. What the registry computes, it can read back."""
    for source in TILE_SOURCES:
        for east, north in ((347, 5647), (690, 5334), (32, 5000)):
            assert tile_of(source, east, north) == (east, north), source.name


def test_a_tile_covers_the_place_it_is_asked_for() -> None:
    """A 2 km scheme names its tiles by the corner, so the tile for 5 647 km is
    the one starting at 5 646 — getting this wrong fetches the neighbour."""
    for source in TILE_SOURCES:
        east, north = source.corner_of(347_500.0, 5_647_800.0)
        assert east * 1000 <= 347_500.0 < (east + source.tile_km) * 1000, source.name
        assert north * 1000 <= 5_647_800.0 < (north + source.tile_km) * 1000, source.name


def test_the_registry_is_read_by_state_and_product() -> None:
    bavarian = sources_for("BY")
    assert {s.product for s in bavarian} >= {TileProduct.DGM1, TileProduct.LOD2}
    assert sources_for("XX") == ()
    # A state with a service already (doc 68) may still have tiles: NRW's point
    # cloud is here because no coverage service serves a point cloud.
    assert any(s.product is TileProduct.LAZ for s in sources_for("NW"))


def test_what_a_number_is_worth_is_recorded() -> None:
    """A raster says its vertical step, a cloud says its density: the page tells
    the gardener how fine the answer is (doc 102)."""
    for source in TILE_SOURCES:
        if source.product is TileProduct.LAZ:
            assert source.points_per_m2 is not None and source.points_per_m2 > 0, source.name
        elif source.product in (TileProduct.DGM1, TileProduct.DOM1):
            assert source.vertical_step_m is not None and source.vertical_step_m > 0, source.name


def test_an_index_is_an_address_of_its_own() -> None:
    for source in TILE_SOURCES:
        if source.index_url is None:
            continue
        assert source.index_url.startswith("https://"), source.name


@pytest.mark.parametrize("name", [s.name for s in TILE_SOURCES])
def test_a_name_is_a_slug_that_says_state_and_product(name: str) -> None:
    assert re.fullmatch(r"[a-z]{2}-[a-z0-9]+", name), name


def test_the_registry_computes_the_addresses_the_probe_got_answers_from() -> None:
    """The point of the whole file. These six strings are what answered 200 on
    2026-09-20 (doc 102); if `url_for` stops producing them, the registry has
    drifted from the thing it claims to describe."""
    answered = {
        "by-dgm1": "https://download1.bayernwolke.de/a/dgm/dgm1/690_5334.tif",
        "by-lod2": "https://download1.bayernwolke.de/a/lod2/citygml/690_5334.gml",
    }
    by_name = {source.name: source for source in TILE_SOURCES}
    for name, url in answered.items():
        assert by_name[name].url_for(690, 5334) == url, name

    nrw = {
        "nw-lod2": ("https://www.opengeodata.nrw.de/produkte/geobasis/3dg/lod2_gml/lod2_gml/"
                    "LoD2_32_347_5647_1_NW.gml"),
        "nw-laz": ("https://www.opengeodata.nrw.de/produkte/geobasis/hm/3dm_l_las/3dm_l_las/"
                   "3dm_32_347_5647_1_nw.laz"),
    }
    for name, url in nrw.items():
        assert by_name[name].url_for(347, 5647) == url, name


def test_the_fallback_names_the_degree_cell_a_garden_is_in() -> None:
    """Copernicus GLO-30, the horizon ring for a state that serves nothing. The
    cell is named by its south-west corner, so Wuppertal is N51 E007."""
    assert glo30_url(51.2564, 7.1501) == (
        "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N51_00_E007_00_DEM/"
        "Copernicus_DSM_COG_10_N51_00_E007_00_DEM.tif")
    # South and west exist, and floor is the rule on both axes.
    assert "S34_00_W059" in glo30_url(-33.4, -58.6)
