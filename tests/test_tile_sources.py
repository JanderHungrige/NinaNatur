"""The tile registry's own rules — Wave 25, feature 0 (doc 102).

Doc 68's three questions asked of files rather than services: may we use it,
does it say whose it is, and does the address we compute match the address the
state publishes. Nothing here touches the network — that is
`scripts/probe_tile_sources.py`, run deliberately, with its date in the doc.
"""
from __future__ import annotations

import re

import pytest
from geokachel.tile_sources import (
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
    """Nearly every scheme in this family is the grid written down, so a tile's
    URL is arithmetic. Nothing user-typed reaches a path."""
    for source in TILE_SOURCES:
        if not source.computed:
            continue
        url = source.url_for(347, 5647)
        assert url.startswith("https://"), source.name
        assert "347" in url or "0347" in url, f"{source.name}: {url}"
        assert "5647" in url, f"{source.name}: {url}"


def test_a_state_that_writes_a_flight_year_says_so_instead_of_pretending() -> None:
    """Rheinland-Pfalz puts the year of the flight in the name, and the tile
    next door was flown in a different year. Such a source has no arithmetic
    address and must refuse to invent one rather than build a plausible 404."""
    looked_up = [s for s in TILE_SOURCES if not s.computed]
    assert looked_up, "the registry has lost its index-driven sources"
    for source in looked_up:
        # Either the state lists its tiles, or its archives do it for it.
        assert source.lookup is not None or source.archives, source.name
        with pytest.raises(ValueError, match="index"):
            source.url_for(347, 5647)


def test_a_state_that_publishes_no_tile_says_which_archives_hold_them() -> None:
    """Hamburg one per product, Saarland one per Landkreis. A zip keeps its
    index at the end, so the archive is its own list of what it holds."""
    archived = [s for s in TILE_SOURCES if s.archives]
    assert archived, "the registry has lost its archive-backed sources"
    for source in archived:
        assert not source.computed, source.name
        for url in source.archives:
            assert url.startswith("https://"), f"{source.name}: {url}"
            assert url.endswith(".zip"), f"{source.name}: {url}"


def test_the_address_a_looked_up_name_goes_into_is_ours() -> None:
    """An index is remote content. What is taken from it is a file name; the
    scheme, the host and the shape of the address stay the registry's own, so
    a state's list can change which file is asked for and never which host is
    asked. A name that arrived pointing somewhere else goes nowhere else."""
    forged = "https://example.invalid/evil.tif"
    for source in TILE_SOURCES:
        if source.lookup is None:
            continue
        assert source.lookup.index_url.startswith("https://"), source.name
        here = source.lookup.index_url.split("/")[2]

        built = source.lookup.address("dgm1_32_419_5490_1_rp_2022.tif", (419, 5490))
        assert built.startswith("https://"), f"{source.name}: {built}"
        assert built.split("/")[2] == here, f"{source.name}: {built}"

        # Even handed a whole URL as the "name", the host is still the state's.
        assert source.lookup.address(forged, (419, 5490)).split("/")[2] == here, source.name


def test_the_tile_name_round_trips_for_every_state_scheme() -> None:
    """Bayern writes `690_5334`, NRW `LoD2_32_347_5647_1_NW`: the same two
    numbers, differently dressed. What the registry computes, it can read back."""
    # Three digits of kilometres, which every German easting in UTM32 and 33
    # is (about 280 to 920). It matters here: Bayern writes the zone onto the
    # front of the easting, and "3232" would be ambiguous in a way no real
    # tile name is.
    for source in TILE_SOURCES:
        if not source.computed:
            continue
        for east, north in ((347, 5647), (690, 5334), (280, 5000), (920, 6100)):
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
        elif source.product in (TileProduct.DGM1, TileProduct.DOM):
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
