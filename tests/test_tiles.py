"""A window built from tiles — Wave 25, feature 1 (doc 103).

No network: the tiles are built here, each carrying its own number, so a test
can say which square kilometre a height came from.
"""
from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import WINDOW_M
from ninanatur.geo.tile_cache import TileCache
from ninanatur.geo.tile_sources import TileProduct, sources_for
from ninanatur.geo.tiles import tile_window, tiles_across
from ninanatur.geo.utm import to_utm

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
