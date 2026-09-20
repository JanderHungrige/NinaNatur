"""The TIFF reader, against files built byte by byte in the test.

No fixtures and no network: the six services disagree in three dimensions —
byte order, sample format, and compression with two different predictors — and
every combination has to be constructible here or it cannot be regression-tested.
The files are built in `tiff_builders.py`, and the LZW stream by an encoder
written from the specification there, not by the decoder under test.
"""
from __future__ import annotations

import time

import numpy as np
import pytest
from geokachel.tiff import TiffError, read_raster
from geokachel.tiff_codec import lzw
from tiff_builders import HEIGHTS, _lzw_encode, _tiff, _tiled


def test_a_plain_little_endian_float_raster() -> None:
    raster = read_raster(_tiff(HEIGHTS))
    assert (raster.width, raster.height) == (3, 2)
    assert raster.values[1][2] == pytest.approx(13.0)


def test_a_big_endian_integer_raster() -> None:
    """Baden-Württemberg's shape. Read as little-endian it gives heights in the
    millions — which is the *good* failure, because it is obvious."""
    metres = np.array([[241, 242], [243, 244]], dtype=">u2")
    raster = read_raster(_tiff(metres, big_endian=True))
    assert raster.values[0][0] == pytest.approx(241)
    assert raster.values[1][1] == pytest.approx(244)


def test_lzw_without_a_predictor() -> None:
    """Nordrhein-Westfalen's shape."""
    raster = read_raster(_tiff(HEIGHTS, compress=True))
    assert raster.values[0][1] == pytest.approx(11.0)


def test_lzw_with_the_floating_point_predictor() -> None:
    """Niedersachsen's shape — and the one that decoded to a median of zero and
    a range of 3e38 before predictor 3 was implemented."""
    raster = read_raster(_tiff(HEIGHTS, compress=True, predictor=3))
    assert raster.values[1][0] == pytest.approx(12.0)
    assert raster.values.max() == pytest.approx(13.0)


@pytest.mark.parametrize("data", [
    b"\x00" * 200_000,
    bytes(range(256)) * 400,
    np.random.default_rng(17).integers(0, 8, 60_000, dtype=np.uint8).tobytes(),
], ids=["a long run", "a sweep that fills the table", "noise"])
def test_codes_widen_where_libtiff_widens_them(data: bytes) -> None:
    """Every earlier test fitted in nine-bit codes, so the early-change rule —
    the part the codec's docstring calls the one everybody gets wrong — had never
    been crossed here. It was on 2026-09-11, and it was the test's encoder that
    had it wrong: it widened one code before libtiff does."""
    assert lzw(_lzw_encode(data)) == data


def test_strip_counts_may_be_shorts_while_offsets_are_longs() -> None:
    """Brandenburg does exactly this in one file. Reading both as longs gave
    plausible-looking garbage lengths and nine times too many values."""
    tall = np.arange(20, dtype="<f4").reshape(10, 2)
    raster = read_raster(_tiff(tall, rows_per_strip=2, short_counts=True))
    assert raster.values[9][1] == pytest.approx(19.0)


def test_nodata_becomes_nan_rather_than_minus_nine_thousand() -> None:
    """Border tiles and water are genuinely empty. A -9999 averaged into a slope
    is a cliff that is not there."""
    with_hole = np.array([[10.0, -9999.0], [11.0, 12.0]], dtype="<f4")
    raster = read_raster(_tiff(with_hole))
    assert np.isnan(raster.values[0][1])
    assert np.nanmax(raster.values) == pytest.approx(12.0)


def test_an_unreadable_file_says_so_rather_than_guessing() -> None:
    with pytest.raises(TiffError):
        read_raster(b"this is not a tiff at all")


# --- packaging and layout --------------------------------------------------

def test_a_tiled_raster_is_reassembled_in_the_right_order() -> None:
    """Sachsen-Anhalt's shape, and the shape of every Cloud-Optimised GeoTIFF —
    which the BKG's own documentation says these products may be delivered as.

    A tile grid pads the last column and the last row out to a whole tile, so
    the padding must be dropped rather than shifted in. Getting that wrong
    skews every row after the first tile boundary by a few metres, which looks
    entirely plausible on a hillside.
    """
    grid = np.arange(200 * 200, dtype="<f4").reshape(200, 200)
    raster = read_raster(_tiled(grid, tile=128))

    assert (raster.width, raster.height) == (200, 200)
    assert raster.values[0][0] == pytest.approx(0.0)
    assert raster.values[0][199] == pytest.approx(199.0), "the padded column"
    assert raster.values[199][0] == pytest.approx(199 * 200.0), "the padded row"
    assert raster.values[150][150] == pytest.approx(150 * 200 + 150.0)


def test_a_multipart_response_is_unwrapped() -> None:
    """WCS 2.0 lets a server package the coverage as multipart/related: a GML
    part describing the grid, then the pixels. Five of the eight services hand
    back a bare GeoTIFF; Sachsen-Anhalt packages it, and is entitled to."""
    inner = _tiff(HEIGHTS)
    wrapped = (
        b"--wcs\r\nContent-Type: text/xml\r\nContent-ID: GML-Part\r\n\r\n"
        b"<gmlcov:RectifiedGridCoverage/>\r\n--wcs\r\n"
        b"Content-Type: image/tiff\r\n\r\n" + inner + b"\r\n--wcs--\r\n"
    )

    raster = read_raster(wrapped)

    assert raster.values[1][2] == pytest.approx(13.0)


def test_a_deflated_tiled_raster_reads_like_any_other() -> None:
    """What a cloud-optimised GeoTIFF is: tiles, packed with deflate rather than
    LZW. Copernicus GLO-30 is written this way, and without it nine states have
    no horizon (doc 104)."""
    side = 32
    values = np.arange(side * side, dtype="<f4").reshape(side, side)
    raster = read_raster(_tiled(values, tile=16, compression=8))
    assert raster.width == raster.height == side
    assert raster.values[0][0] == pytest.approx(0.0)
    assert raster.values[side - 1][side - 1] == pytest.approx(side * side - 1)


def test_a_whole_degree_cell_is_refused_unless_the_caller_asks_for_one() -> None:
    """Wave 20's guard stays tight for every window; a caller reading a whole
    product says so, and only then (doc 104)."""
    from geokachel.tiff import MAX_PIXELS, WHOLE_TILE_PIXELS

    assert WHOLE_TILE_PIXELS > 2400 * 3600 > MAX_PIXELS
    big = _tiled(np.zeros((2100, 2100), dtype="<f4"), tile=1024, compression=8)
    with pytest.raises(TiffError, match="more than this caller asks for"):
        read_raster(big)
    wide = read_raster(big, max_pixels=WHOLE_TILE_PIXELS)
    assert wide.width == wide.height == 2100


# --- The decoder has to survive a whole tile, not just a window (doc 103) ---

def _lzw_literals(payload: bytes) -> bytes:
    """A real TIFF-LZW stream of literal codes, encoded the way the decoder
    expects to read it — nine bits growing to twelve, with the early change.

    Written here rather than kept as a fixture because what matters is the
    *length*: a megabyte of codes is what turned the decoder quadratic, and a
    megabyte of real tile in the repository would be a megabyte in the repo.
    """
    out, value, held = bytearray(), 0, 0
    table_len, width, started = 258, 9, False

    def emit(code: int) -> None:
        nonlocal value, held
        value = (value << width) | code
        held += width
        while held >= 8:
            out.append((value >> (held - 8)) & 0xFF)
            held -= 8
            value &= (1 << held) - 1

    emit(256)  # clear
    for byte in payload:
        emit(byte)
        if started:
            table_len += 1
        started = True
        if table_len + 1 >= (1 << width) and width < 12:
            width += 1
    emit(257)  # end of information
    if held:
        out.append((value << (8 - held)) & 0xFF)
    return bytes(out)


def test_a_whole_tile_of_lzw_decodes_in_a_moment_not_in_minutes() -> None:
    """Wave 25's tiles are whole square kilometres, where every service before
    them answered with a 400 m window. A megabyte of LZW is the difference.

    The decoder used to keep every byte the stream had ever held in one Python
    integer, so each shift cost the whole of it and the loop was quadratic:
    Hamburg's square kilometre took **492 seconds**, and Sachsen's four square
    kilometres would have taken half an hour. Masking off the bits already
    consumed made it 0.58 s. The bound below is loose enough never to flake and
    far tighter than the bug.
    """
    payload = bytes(range(256)) * 4_000  # a megabyte, as a tile's strip is
    stream = _lzw_literals(payload)

    started = time.monotonic()
    assert lzw(stream) == payload
    assert time.monotonic() - started < 10.0, "the LZW decoder has gone quadratic again"
