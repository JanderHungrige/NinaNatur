"""The TIFF reader, against files built byte by byte in the test.

No fixtures and no network: the six services disagree in three dimensions —
byte order, sample format, and compression with two different predictors — and
every combination has to be constructible here or it cannot be regression-tested.
The files are built in `tiff_builders.py`, and the LZW stream by an encoder
written from the specification there, not by the decoder under test.
"""
from __future__ import annotations

import numpy as np
import pytest
from tiff_builders import HEIGHTS, _lzw_encode, _tiff, _tiled

from ninanatur.geo.tiff import TiffError, read_raster
from ninanatur.geo.tiff_codec import lzw


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
