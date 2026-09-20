"""A window built from tiles — Wave 25, feature 1 (doc 103).

No network: the tiles are built here, each carrying its own number, so a test
can say which square kilometre a height came from.
"""
from __future__ import annotations

import io
import struct
import zipfile
from pathlib import Path

import numpy as np
import pytest

from ninanatur.geo import tiles
from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import WINDOW_M, TerrainWindow
from ninanatur.geo.tile_cache import TileCache
from ninanatur.geo.tile_sources import TileProduct, sources_for
from ninanatur.geo.tiles import corner_in, surface_window, tile_window, tiles_across
from ninanatur.geo.utm import to_latlon, to_utm

BAYERN = next(s for s in sources_for("BY") if s.product is TileProduct.DGM1)
#: A garden in Munich, in the middle of its square kilometre.
MUNICH = LatLon(lat=48.137, lon=11.575)
#: And one that happens to sit within a metre of a tile corner — UTM32
#: 693 000.0 E, 5 332 000.9 N — whose window spans four of them.
CORNER = LatLon(lat=48.112, lon=11.593)


def _tiff(values: np.ndarray) -> bytes:
    """A plain little-endian float32 TIFF, one strip — as `test_terrain` does."""
    height, width = values.shape
    body = values.astype("<f4").tobytes()
    entries = [
        (256, width), (257, height), (258, 32), (259, 1),
        (273, 8), (277, 1), (278, height), (279, len(body)), (339, 3),
    ]
    out = bytearray(b"II\x2a\x00") + struct.pack("<I", 8 + len(body)) + body
    out += struct.pack("<H", len(entries))
    for tag, value in entries:
        kind = 4 if tag in (273, 279) else 3
        raw = struct.pack("<I" if kind == 4 else "<H", value)
        out += struct.pack("<HHI", tag, kind, 1) + raw + b"\x00" * (4 - len(raw))
    out += struct.pack("<I", 0)
    return bytes(out)


def _tile_of(url: str) -> bytes:
    """Every tile is flat, at a height that says which tile it is: the last two
    digits of its easting and northing, so a mosaic can be read back."""
    name = url.rsplit("/", 1)[-1].split(".")[0]
    east, north = (int(part) for part in name.split("_"))
    return _tiff(np.full((1000, 1000), float(east % 100 * 100 + north % 100), dtype="<f4"))


def _cache(tmp_path: Path) -> TileCache:
    return TileCache(tmp_path, cap_bytes=50_000_000)


def test_a_window_in_the_middle_of_a_tile_needs_one(tmp_path: Path) -> None:
    east, north = 690_500.0, 5_334_500.0
    assert tiles_across(east, north, BAYERN, WINDOW_M) == [(690, 5334)]


def test_a_window_at_a_corner_needs_four(tmp_path: Path) -> None:
    """A 200 m window in a 1 km tile fits inside one only when the garden is
    100 m from every edge — 64 % of the time, and the rest of the time a
    missing tile is missing ground on one side of the garden."""
    corner = tiles_across(690_050.0, 5_334_950.0, BAYERN, WINDOW_M)
    assert sorted(corner) == [(689, 5334), (689, 5335), (690, 5334), (690, 5335)]
    edge = tiles_across(690_500.0, 5_334_950.0, BAYERN, WINDOW_M)
    assert sorted(edge) == [(690, 5334), (690, 5335)]


def test_the_window_is_pasted_from_every_tile_it_touches(tmp_path: Path) -> None:
    """Each tile here is flat at a height that names it, so what the window
    holds says which square kilometres it was pasted from. Which corner is in
    which tile is not asserted: the garden's frame is rotated against UTM by up
    to 2.3°, so a point within a few metres of a tile line may be either side
    of it, and that is the resampling working, not failing."""
    east, north = to_utm(CORNER.lat, CORNER.lon, 32)
    wanted = {e % 100 * 100 + n % 100
              for e, n in tiles_across(east, north, BAYERN, WINDOW_M)}
    window = tile_window(CORNER, BAYERN, cache=_cache(tmp_path), fetch=_tile_of)
    assert window is not None
    held = {value for value in window.heights if value == value}  # noqa: PLR0124 - not NaN
    assert held == wanted, (held, wanted)
    assert len(wanted) > 1, "pick a garden near a tile line, or this proves nothing"


def test_the_window_carries_the_registry_s_provenance(tmp_path: Path) -> None:
    """A Munich garden's page says whose ground it is standing on."""
    window = tile_window(MUNICH, BAYERN, cache=_cache(tmp_path), fetch=_tile_of)
    assert window is not None
    assert window.licence == "CC-BY-4.0"
    assert "Bayerische Vermessungsverwaltung" in window.attribution
    assert window.source == "BY"
    assert window.cell_m == 1.0
    assert window.cols == window.rows == int(2 * WINDOW_M)


def test_a_tile_that_is_not_there_leaves_the_ground_unknown(tmp_path: Path) -> None:
    """A state's portal missing one tile of four is not a reason to have no
    ground at all — the window keeps what arrived and says NaN for the rest."""
    def patchy(url: str) -> bytes:
        if url.endswith("692_5331.tif"):  # one of the corner's four
            raise FileNotFoundError(url)
        return _tile_of(url)

    window = tile_window(CORNER, BAYERN, cache=_cache(tmp_path), fetch=patchy)
    assert window is not None
    known = [value for value in window.heights if value == value]  # noqa: PLR0124
    assert known, "the tiles that did arrive are still ground"
    assert len(known) < len(window.heights), "and the one that did not is NaN"


def test_nothing_arrives_at_all_and_the_answer_is_none(tmp_path: Path) -> None:
    def gone(url: str) -> bytes:
        raise FileNotFoundError(url)

    assert tile_window(MUNICH, BAYERN, cache=_cache(tmp_path), fetch=gone) is None


def test_a_state_with_no_surface_service_gets_one_from_its_tiles(tmp_path: Path) -> None:
    """Feature 5 (doc 108): Bayern publishes a twenty-centimetre surface model
    as tiles and runs no coverage service anybody may use, so until now the
    biggest state in the country found no trees at all."""
    from ninanatur.geo.terrain import TerrainWindow
    from ninanatur.geo.tile_sources import TileProduct
    from ninanatur.geo.tiles import surface_window

    source = next(s for s in sources_for("BY") if s.product is TileProduct.DOM)
    assert source.cell_m == 0.2

    # Ground at 500 m, and a tile whose every pixel is eight metres above it.
    ground = TerrainWindow(
        min_x=-100.0, min_y=-100.0, cell_m=1.0, cols=200, rows=200,
        heights=[500.0] * (200 * 200), source="BY", licence="CC-BY-4.0",
        attribution="Bayerische Vermessungsverwaltung", vertical_step_m=0.01,
    )
    side = int(1000 / source.cell_m)
    tile = _tiff(np.full((side, side), 508.0, dtype="<f4"))

    window = surface_window(MUNICH, source, ground, cache=_cache(tmp_path),
                            fetch=lambda _url: tile)
    assert window is not None
    assert window.cell_m == 0.2
    # Above the ground, not above the sea: that subtraction is the whole point.
    assert window.at(0.0, 0.0) == pytest.approx(8.0, abs=0.01)
    assert window.licence == "CC-BY-4.0"


def test_surface_tiles_without_the_ground_are_no_answer(tmp_path: Path) -> None:
    """A surface model is metres above sea level. Without the terrain under it
    there is nothing to subtract, and a height above the sea says nothing about
    what stands in a garden."""
    from ninanatur.garden.building_sync import _surface_from_tiles

    assert _surface_from_tiles(MUNICH, "Bayern", None) is None


# --- Tiles that arrive in an archive (doc 103, the zipping states) ---

THURINGIA = next(s for s in sources_for("TH") if s.product is TileProduct.DGM1)
BADEN = next(s for s in sources_for("BW") if s.product is TileProduct.DOM)


def _archived(url: str, *, members: int = 1) -> bytes:
    """What Thüringen and Baden-Württemberg actually serve: the tile beside the
    same heights as text, a licence and a metadata file — and, in Baden-
    Württemberg, four one-kilometre tiles in one two-kilometre archive."""
    stem = url.rsplit("/", 1)[-1].removesuffix(".zip")
    east, north = corner_in(stem, (0, 0))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{stem}/Datenlizenz_Deutschland.pdf", b"%PDF-1.4 not a tile")
        if members == 1:
            archive.writestr(f"{stem}.tif", _flat(east, north))
            archive.writestr(f"{stem}.xyz", b"561000.50 5609000.50 214.77\n")
            archive.writestr(f"{stem}.meta", b"Genauigkeit Hoehe: 0.15-0.30m")
        else:
            for down in (0, 1):
                for across in (0, 1):
                    part = f"{stem}/ndom1_32_{east + across}_{north + down}_1_bw"
                    archive.writestr(f"{part}.tif", _flat(east + across, north + down))
                    archive.writestr(f"{part}.csv", b"Kachel;Stand\n")
    return out.getvalue()


def _flat(east: int, north: int) -> bytes:
    """A tile whose every height says which tile it is."""
    return _tiff(np.full((1000, 1000), float(east % 100 * 100 + north % 100), dtype="<f4"))


def test_a_zipped_tile_is_read_through_its_wrapper(tmp_path: Path) -> None:
    """Thüringen wraps its GeoTIFF with the same heights again as a 29 MB .xyz
    and a .meta. The grid is unchanged, so the window is the same window — and
    the text copy is never the thing that is read."""
    erfurt = LatLon(lat=50.978, lon=11.029)
    window = tile_window(erfurt, THURINGIA, cache=_cache(tmp_path), fetch=_archived)
    assert window is not None
    assert window.source == "TH"
    assert np.isfinite(window.heights).all()
    east, north = to_utm(erfurt.lat, erfurt.lon, 32)
    marks = {float(e % 100 * 100 + n % 100)
             for e, n in tiles_across(east, north, THURINGIA, WINDOW_M)}
    assert set(window.heights) <= marks


def test_the_archive_is_what_is_cached_not_what_is_in_it(tmp_path: Path) -> None:
    """The cache holds what arrived, so a second garden on the same street
    fetches nothing — and the wrapper is taken off on the way out each time."""
    cache = _cache(tmp_path)
    asked: list[str] = []

    def once(url: str) -> bytes:
        asked.append(url)
        return _archived(url)

    erfurt = LatLon(lat=50.978, lon=11.029)
    assert tile_window(erfurt, THURINGIA, cache=cache, fetch=once) is not None
    first = len(asked)
    assert tile_window(erfurt, THURINGIA, cache=cache, fetch=once) is not None
    assert len(asked) == first
    assert list(tmp_path.rglob("*.zip"))


def test_four_tiles_in_one_archive_land_where_their_own_names_say(
        tmp_path: Path) -> None:
    """Baden-Württemberg's two-kilometre archive holds four one-kilometre
    tiles. Pasted at the archive's corner they would be stacked on top of each
    other; each one goes where its own name puts it."""
    east, north = 514_000.0, 5_405_000.0  # the point where all four meet
    lat, lon = to_latlon(east, north, 32)
    window = tile_window(LatLon(lat=lat, lon=lon), BADEN, cache=_cache(tmp_path),
                         fetch=lambda url: _archived(url, members=4))
    assert window is not None
    assert np.isfinite(window.heights).all(), "a stacked paste leaves three quarters empty"
    last = window.rows - 1
    corners = [window.heights[0], window.heights[window.cols - 1],
               window.heights[last * window.cols],
               window.heights[last * window.cols + window.cols - 1]]
    # South-west, south-east, north-west, north-east, each its own tile's mark.
    assert corners == [1304.0, 1404.0, 1305.0, 1405.0], corners


def test_the_grid_a_member_name_carries_is_read_back() -> None:
    """Every real member name from the states that zip, read on 2026-09-20."""
    assert corner_in("dgm1_32_561_5609_1_th_2020-2025.tif", (0, 0)) == (561, 5609)
    assert corner_in("dgm1_33278_5590_2_sn.tif", (0, 0)) == (278, 5590)
    assert corner_in("dgm_33250-5888.tif", (0, 0)) == (250, 5888)
    assert corner_in("ndom1_32_513_5405_1_bw.tif", (0, 0)) == (513, 5405)
    # The folder Baden-Württemberg wraps them in is named after the *archive*,
    # and reading that instead would stack all four on one corner.
    assert corner_in("ndom1_32_513_5404_2_bw/ndom1_32_514_5405_1_bw.tif",
                     (0, 0)) == (514, 5405)
    assert corner_in("LoD2_33_372_5808_1_BE.xml", (0, 0)) == (372, 5808)
    # Nothing to read is the archive's own corner, which is every other state.
    assert corner_in("Datenlizenz_Deutschland.pdf", (690, 5334)) == (690, 5334)


def test_a_canopy_height_model_does_not_have_the_ground_taken_off_twice(
        tmp_path: Path) -> None:
    """Baden-Württemberg's nDOM1 is already metres above the ground. Every
    other surface product is metres above the sea, and subtracting a garden's
    terrain from a height that is already relative buries the trees."""
    ground = TerrainWindow(min_x=-200.0, min_y=-200.0, cell_m=1.0, cols=400, rows=400,
                           heights=[300.0] * (400 * 400), source="BW",
                           licence="dl-de/by-2-0", attribution="LGL", vertical_step_m=0.01)
    lat, lon = to_latlon(514_000.0, 5_405_000.0, 32)
    window = surface_window(LatLon(lat=lat, lon=lon), BADEN, ground,
                            cache=_cache(tmp_path),
                            fetch=lambda url: _archived(url, members=4))
    assert window is not None
    # The tile markers are tens of metres; had the 300 m ground been taken off
    # a second time, every one of them would be zero after the clamp.
    assert np.isfinite(window.heights).all()
    assert set(window.heights) == {
        float(e % 100 * 100 + n % 100)
        for e, n in ((513, 5404), (513, 5405), (514, 5404), (514, 5405))}


# --- Tiles found through a state's list, not computed (doc 103) ---

RHINELAND = next(s for s in sources_for("RP") if s.product is TileProduct.DGM1)
METALINK = Path(__file__).parent / "fixtures" / "rp_dgm1_metalink.meta4"


def _listed(url: str) -> bytes:
    """The state's own metalink, then flat tiles for whatever it names."""
    if url.endswith(".meta4"):
        return METALINK.read_bytes()
    return _tiff(np.full((1000, 1000), 150.0, dtype="<f4"))


@pytest.fixture(autouse=True)
def _forget_listings() -> None:
    """What was parsed is kept for the life of the process, so a test must not
    inherit another test's."""
    tiles._LISTINGS.clear()
    tiles._HELD.clear()


def test_a_tile_is_found_through_the_states_own_list(tmp_path: Path) -> None:
    """Rheinland-Pfalz writes the flight year into the name — 419/5490 was
    flown in 2022 and its neighbour in 2025 — so the address is the registry's
    own folder plus a name the state's metalink gave us."""
    asked: list[str] = []

    def fetch(url: str) -> bytes:
        asked.append(url)
        return _listed(url)

    lat, lon = to_latlon(419_500.0, 5_490_500.0, 32)
    window = tile_window(LatLon(lat=lat, lon=lon), RHINELAND, cache=_cache(tmp_path),
                         fetch=fetch)
    assert window is not None
    assert window.source == "RP"
    assert asked == [
        "https://geobasis-rlp.de/data/dgm1/current/meta4/dgm1_tif_07.meta4",
        "https://geobasis-rlp.de/data/dgm1/current/tif/dgm1_32_419_5490_1_rp_2022.tif",
    ]


def test_the_list_is_read_once_however_many_gardens_ask(tmp_path: Path) -> None:
    """Twelve megabytes of XML and twenty-one thousand names is a thing to read
    once for a deployment, not once for a garden."""
    asked: list[str] = []

    def fetch(url: str) -> bytes:
        asked.append(url)
        return _listed(url)

    lat, lon = to_latlon(419_500.0, 5_490_500.0, 32)
    for _ in range(3):
        assert tile_window(LatLon(lat=lat, lon=lon), RHINELAND,
                           cache=_cache(tmp_path), fetch=fetch) is not None
    assert sum(1 for url in asked if url.endswith(".meta4")) == 1


def test_a_square_the_state_does_not_list_is_not_asked_for(tmp_path: Path) -> None:
    """Its own list says it has nothing there — a gap in a flight, or a garden
    near the border. Guessing a name would be a 404 with extra steps."""
    asked: list[str] = []

    def fetch(url: str) -> bytes:
        asked.append(url)
        return _listed(url)

    lat, lon = to_latlon(500_500.0, 5_500_500.0, 32)
    assert tile_window(LatLon(lat=lat, lon=lon), RHINELAND,
                       cache=_cache(tmp_path), fetch=fetch) is None
    assert [url for url in asked if not url.endswith(".meta4")] == []


# --- Tiles read out of an archive that is never fetched (doc 103) ---

SAARLAND = next(s for s in sources_for("SL") if s.product is TileProduct.DGM1)


class _Share:
    """A state's file host, serving ranges over one archive and keeping the
    bill. The other five districts are not there, which is a region without
    ground rather than a state without ground."""

    def __init__(self, corners: list[tuple[int, int]]) -> None:
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
            for east, north in corners:
                archive.writestr(f"DGM1_tif_NK/dgm1_32_{east}_{north}_1_SL_2025.tif",
                                 _flat(east, north))
        self.body = out.getvalue()
        self.here = SAARLAND.archives[1]
        self.served = 0

    def size(self, url: str) -> int:
        if url != self.here:
            raise OSError(f"no such archive: {url}")
        return len(self.body)

    def ranged(self, url: str, start: int, end: int) -> bytes:
        if url != self.here:
            raise OSError(f"no such archive: {url}")
        self.served += end - start + 1
        return self.body[start:end + 1]


def test_a_tile_is_read_out_of_an_archive_that_is_never_fetched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Saarland publishes nothing smaller than a 559 MB Landkreis. Its own
    directory says what is in it, and the tile comes out of it by range.

    What this checks is that the path is right: the window is the tile, and the
    whole-file fetcher is never called. That the cost is a fraction of the
    archive is `test_remote_zip`, whose archive is incompressible and therefore
    the size a real one is — four identical tiles deflate to nothing, and a
    cost assertion over them would pass for the wrong reason."""
    share = _Share([(348, 5475), (349, 5475), (348, 5476), (349, 5476)])
    monkeypatch.setattr(tiles, "size_of", share.size)
    monkeypatch.setattr(tiles, "get_range", share.ranged)

    lat, lon = to_latlon(348_500.0, 5_475_500.0, 32)
    window = tile_window(LatLon(lat=lat, lon=lon), SAARLAND, cache=_cache(tmp_path),
                         fetch=_never)
    assert window is not None
    assert window.source == "SL"
    assert np.isfinite(window.heights).all()
    assert set(window.heights) == {float(48 * 100 + 75)}
    assert share.served > 0


def test_a_district_whose_archive_is_missing_is_a_gap_not_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Five of Saarland's six archives are absent in this test. A garden in the
    sixth still gets its ground, and one elsewhere gets None rather than an
    error — the same answer as a state with no source at all."""
    share = _Share([(348, 5475)])
    monkeypatch.setattr(tiles, "size_of", share.size)
    monkeypatch.setattr(tiles, "get_range", share.ranged)

    lat, lon = to_latlon(600_500.0, 5_500_500.0, 32)
    assert tile_window(LatLon(lat=lat, lon=lon), SAARLAND,
                       cache=_cache(tmp_path), fetch=_never) is None


def _never(url: str) -> bytes:
    raise AssertionError(f"an archived tile must not be fetched whole: {url}")
