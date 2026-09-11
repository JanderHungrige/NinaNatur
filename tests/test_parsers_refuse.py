"""Parsers that refuse — Wave 20, feature 8.

The app reads two formats it did not write, from services it does not run:
CityGML tiles from Nordrhein-Westfalen's LoD2 store (tens of megabytes) and
GeoTIFF windows from eight state surveys. Both answers are cached, so a hostile
one — a compromised survey, a man in the middle — is replayed on every rerun.

Found by reading on 2026-09-11, before any of this:

- `lod2.buildings_from` parsed the tile with the standard library, which accepts
  a DTD and expands the entities it declares.
- `get_bytes` read an answer of any size into memory.
- `tiff._tiles` allocated width × height bytes, both straight from the file,
  before reading a byte of pixels — and that runs in the request thread, where a
  container that reaches its memory limit loses the whole app, not a worker.
- `tiff_codec.lzw` let its table grow past the 4,096 entries TIFF allows, with
  no bound on its output: a quarter-megabyte strip can decode to hundreds of MB.
- A malformed offset surfaced as `struct.error`, not as `TiffError`.

Every failure has to end the way the model already documents: the garden keeps
its flat ground, or its assumed heights. The fuzz test at the end is bounded — a
few thousand seeded mutations, in seconds — and must never be run against the
reader as it was before the bounds: a mutated width there asks for gigabytes.
"""
from __future__ import annotations

import random
import struct
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pytest
import requests
from test_lod2 import HEAD, ROOF, SQUARE, TAIL, _building, _surface
from tiff_builders import HEIGHTS, _lzw_encode, _tiff, _tiled

from ninanatur.garden import building_sync
from ninanatur.geo import lod2, tiff
from ninanatur.geo.lod2 import Lod2Error, buildings_from
from ninanatur.geo.projection import LatLon
from ninanatur.geo.tiff import TiffError, read_raster
from ninanatur.geo.tiff_codec import TiffCodecError, lzw
from ninanatur.ingest import http

VALID = HEAD + _building(
    "DE_1", "3100", "9.5", _surface("GroundSurface", SQUARE) + _surface("RoofSurface", ROOF)
) + TAIL
LAUGHS = ('<!DOCTYPE core:CityModel [<!ENTITY a "haha">'
          '<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
          '<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">]>')
EXTERNAL = '<!DOCTYPE core:CityModel [<!ENTITY secret SYSTEM "file:///etc/passwd">]>'


def _with_doctype(doctype: str) -> bytes:
    """A DTD goes after the XML declaration and before the root element."""
    text = VALID
    if text.startswith("<?xml"):
        end = text.index("?>") + 2
        return (text[:end] + doctype + text[end:]).encode()
    return (doctype + text).encode()


# --- CityGML -------------------------------------------------------------------------

def test_the_tile_the_tests_build_is_a_tile_the_reader_reads() -> None:
    """The control: without it, every refusal below could be a broken fixture."""
    assert [b.building_id for b in buildings_from(VALID.encode())] == ["DE_1"]


def test_a_tile_that_declares_entities_is_refused() -> None:
    """A survey tile has no DTD. One that carries a DTD is not a survey tile."""
    with pytest.raises(Lod2Error):
        buildings_from(_with_doctype(LAUGHS))


def test_a_tile_that_names_a_file_on_this_machine_is_refused() -> None:
    with pytest.raises(Lod2Error):
        buildings_from(_with_doctype(EXTERNAL))


def test_a_tile_larger_than_any_real_one_is_refused_before_it_is_parsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lod2, "MAX_TILE_BYTES", 100)
    with pytest.raises(Lod2Error):
        buildings_from(VALID.encode())


def test_a_hostile_tile_leaves_the_garden_with_its_assumed_heights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The documented degradation, through the one caller that exists."""
    monkeypatch.setattr(building_sync, "get_bytes", lambda *_a, **_k: _with_doctype(LAUGHS))
    assert building_sync._surveyed(LatLon(lat=51.2564, lon=7.1501), "Nordrhein-Westfalen") is None


# --- what may be fetched at all ----------------------------------------------------------

def _answer(body: bytes, *, declared: str | None = None) -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    response.url = "https://example.test/tile"
    response._content = body
    response._content_consumed = True
    if declared is not None:
        response.headers["Content-Length"] = declared
    return response


@pytest.fixture()
def quiet(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    monkeypatch.setenv(http.CACHE_DIR_ENV, str(tmp_path / "cache"))
    return tmp_path / "cache"


def test_an_answer_larger_than_its_cap_is_refused_and_not_cached(
    quiet: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(requests, "get", lambda *_a, **_k: _answer(b"x" * 5000))
    with pytest.raises(http.HttpError):
        http.get_bytes("https://example.test/tile", max_bytes=1000)
    assert not list(quiet.glob("*"))


def test_a_declared_length_over_the_cap_is_refused_before_anything_is_read(
    quiet: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(requests, "get", lambda *_a, **_k: _answer(b"", declared="999999999"))
    with pytest.raises(http.HttpError):
        http.get_bytes("https://example.test/tile", max_bytes=1000)


# --- GeoTIFF: targeted -----------------------------------------------------------------------

def _retag(data: bytes, tag: int, value: int) -> bytes:
    """Rewrite one directory entry's value — the way a hostile answer would."""
    end = "<" if data[:2] == b"II" else ">"
    out = bytearray(data)
    at = struct.unpack_from(end + "I", out, 4)[0]
    for i in range(struct.unpack_from(end + "H", out, at)[0]):
        entry = at + 2 + i * 12
        if struct.unpack_from(end + "H", out, entry)[0] == tag:
            code = {3: "H", 4: "I"}[struct.unpack_from(end + "H", out, entry + 2)[0]]
            out[entry + 8 : entry + 12] = struct.pack(end + code, value).ljust(4, b"\x00")
            return bytes(out)
    raise AssertionError(f"tag {tag} is not in the file")


SQUARE_16 = np.arange(16, dtype="<f4").reshape(4, 4)
FIELD_20 = np.arange(400, dtype="<f4").reshape(20, 20)
MALFORMED = {
    "cut off inside its directory": _tiff(HEIGHTS)[:-10],
    "a directory beyond the end": _tiff(HEIGHTS)[:4] + struct.pack("<I", 10_000_000)
    + _tiff(HEIGHTS)[8:],
    "strip offsets beyond the end": _retag(_tiff(SQUARE_16, rows_per_strip=1), 273, 10_000_000),
    "a strip longer than the file": _retag(_tiff(HEIGHTS), 279, 10_000_000),
    "tiles that do not cover the image": _retag(_tiled(FIELD_20, tile=16), 322, 8),
}


@pytest.mark.parametrize("data", MALFORMED.values(), ids=MALFORMED.keys())
def test_every_malformed_file_ends_as_a_tiff_error(data: bytes) -> None:
    """One failure the callers know to catch, not whatever the struct module or
    an index happened to raise."""
    with pytest.raises(TiffError):
        read_raster(data)


def test_a_raster_bigger_than_any_request_is_refused_before_anything_is_allocated() -> None:
    """The largest request here, the horizon ring, is about 504 × 504. A tile
    header claiming 3000 × 3000 is refused while it is still a header."""
    data = _retag(_retag(_tiled(FIELD_20, tile=16), 256, 3000), 257, 3000)
    tracemalloc.start()
    try:
        with pytest.raises(TiffError):
            read_raster(data)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 2_000_000, f"{peak / 1e6:.0f} MB allocated for a file that was refused"


def test_lzw_stops_at_the_limit_it_is_given() -> None:
    stream = _lzw_encode(b"\x00" * 200_000)
    assert len(stream) < 20_000, "the premise: a small stream that expands a lot"
    with pytest.raises(TiffCodecError):
        lzw(stream, limit=10_000)
    assert lzw(stream, limit=200_000) == b"\x00" * 200_000


# --- GeoTIFF: fuzzed -------------------------------------------------------------------------

SEEDS = {
    "float strips": _tiff(HEIGHTS),
    "big-endian integers": _tiff(np.array([[241, 242, 243], [244, 245, 246]], dtype="<u2"),
                                 big_endian=True),
    "lzw with the float predictor": _tiff(HEIGHTS, compress=True, predictor=3),
    "lzw, several strips": _tiff(np.arange(64, dtype="<f4").reshape(8, 8), compress=True,
                                 rows_per_strip=2),
    "tiled": _tiled(FIELD_20, tile=16),
}


def _mutate(data: bytes, rng: random.Random) -> bytes:
    out = bytearray(data)
    how = rng.randrange(5)
    if how == 0:
        for _ in range(rng.randint(1, 8)):
            out[rng.randrange(len(out))] = rng.randrange(256)
    elif how == 1:
        del out[rng.randrange(2, len(out)) :]
    elif how == 2:
        at = rng.randrange(0, len(out) - 4)
        out[at : at + 4] = struct.pack(
            "<I", rng.choice([0xFFFFFFFF, 0x7FFFFFFF, len(out) * 1000, 65535, 4096]))
    elif how == 3:
        at = rng.randrange(0, len(out) - 4)
        out[at : at + 4] = struct.pack("<I", rng.randrange(0, 64))
    else:
        at = rng.randrange(len(out))
        out[at:at] = bytes(rng.randrange(256) for _ in range(rng.randint(1, 32)))
    return bytes(out)


def test_three_thousand_mangled_tiles_end_as_a_raster_or_a_tiff_error() -> None:
    """Seeded, so a failure is a case number that can be replayed."""
    rng = random.Random(20260911)
    names = sorted(SEEDS)
    surprises: list[str] = []
    started = time.perf_counter()
    for case in range(3000):
        name = rng.choice(names)
        data = _mutate(SEEDS[name], rng)
        try:
            raster = read_raster(data)
        except TiffError:
            continue
        except Exception as exc:  # noqa: BLE001 - collecting exactly these is the test
            surprises.append(f"case {case} ({name}): {type(exc).__name__}: {exc}")
            continue
        assert raster.values.shape == (raster.height, raster.width)
        assert raster.width * raster.height <= tiff.MAX_PIXELS
    assert not surprises, "\n".join(surprises[:10])
    assert time.perf_counter() - started < 60, "bounded means bounded in time too"
