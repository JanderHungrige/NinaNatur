"""The TIFF reader, against files built byte by byte in the test.

No fixtures and no network: the six services disagree in three dimensions —
byte order, sample format, and compression with two different predictors — and
every combination has to be constructible here or it cannot be regression-tested.

The LZW stream is produced by an encoder written from the specification in
`_lzw_encode` below. Encoding and decoding are different enough algorithms that
agreeing on the early-change rule is evidence rather than a shared assumption.
"""
from __future__ import annotations

import struct

import numpy as np
import pytest

from ninanatur.geo.tiff import TiffError, read_raster


def _lzw_encode(data: bytes) -> bytes:
    """TIFF LZW, written from the spec to check the decoder against."""
    table = {bytes([i]): i for i in range(256)}
    nxt, width = 258, 9
    out, held, bits = bytearray(), 0, 0

    def emit(code: int, width: int) -> None:
        nonlocal held, bits
        held = (held << width) | code
        bits += width
        while bits >= 8:
            out.append((held >> (bits - 8)) & 0xFF)
            bits -= 8

    emit(256, width)
    current = b""
    for byte in data:
        nextt = current + bytes([byte])
        if nextt in table:
            current = nextt
            continue
        emit(table[current], width)
        table[nextt] = nxt
        nxt += 1
        if nxt + 1 >= (1 << width) and width < 12:
            width += 1
        current = bytes([byte])
    if current:
        emit(table[current], width)
    emit(257, width)
    if bits:
        out.append((held << (8 - bits)) & 0xFF)
    return bytes(out)


def _tiff(
    values: np.ndarray,
    *,
    big_endian: bool = False,
    compress: bool = False,
    predictor: int = 1,
    short_counts: bool = False,
    rows_per_strip: int | None = None,
) -> bytes:
    """A single-band TIFF holding `values`, assembled to order."""
    end = ">" if big_endian else "<"
    height, width = values.shape
    bits = values.dtype.itemsize * 8
    fmt = 3 if values.dtype.kind == "f" else 1
    rows_per_strip = rows_per_strip or height

    body = values.astype(end + values.dtype.str[1:]).tobytes()
    row_bytes = width * (bits // 8)
    strips = [
        body[i * row_bytes : (i + rows_per_strip) * row_bytes]
        for i in range(0, height, rows_per_strip)
    ]
    if predictor == 3:
        strips = [_apply_float_predictor(s, end, width, bits) for s in strips]
    if compress:
        strips = [_lzw_encode(s) for s in strips]

    entries = [
        (256, 3, 1, width), (257, 3, 1, height), (258, 3, 1, bits),
        (259, 3, 1, 5 if compress else 1), (277, 3, 1, 1),
        (278, 3, 1, rows_per_strip), (317, 3, 1, predictor), (339, 3, 1, fmt),
    ]
    header = 8
    dir_at = header + sum(len(s) for s in strips)
    n = len(entries) + 2
    arrays_at = dir_at + 2 + n * 12 + 4

    offsets, at = [], header
    for s in strips:
        offsets.append(at)
        at += len(s)
    counts = [len(s) for s in strips]

    out = bytearray(b"MM\x00\x2a" if big_endian else b"II\x2a\x00")
    out += struct.pack(end + "I", dir_at)
    for s in strips:
        out += s

    def field(tag: int, kind: int, count: int, value: int) -> bytes:
        code = {1: "B", 3: "H", 4: "I"}[kind]
        raw = struct.pack(end + code, value)
        return struct.pack(end + "HHI", tag, kind, count) + raw + b"\x00" * (4 - len(raw))

    off_kind, off_code = 4, "I"
    cnt_kind, cnt_code = (3, "H") if short_counts else (4, "I")
    body_arrays = b""
    all_entries = list(entries)
    if len(strips) == 1:
        all_entries += [(273, off_kind, 1, offsets[0]), (279, cnt_kind, 1, counts[0])]
    else:
        all_entries += [(273, off_kind, len(strips), arrays_at),
                        (279, cnt_kind, len(strips), arrays_at + 4 * len(strips))]
        body_arrays = (struct.pack(end + f"{len(strips)}{off_code}", *offsets)
                       + struct.pack(end + f"{len(strips)}{cnt_code}", *counts))
    all_entries.sort()

    out += struct.pack(end + "H", len(all_entries))
    for tag, kind, count, value in all_entries:
        out += field(tag, kind, count, value)
    out += struct.pack(end + "I", 0)
    out += body_arrays
    return bytes(out)


def _apply_float_predictor(raw: bytes, end: str, width: int, bits: int) -> bytes:
    per = bits // 8
    rows = np.frombuffer(raw, dtype=np.uint8).reshape(-1, width * per)
    out = []
    for row in rows:
        samples = row.reshape(width, per)
        planes = samples[:, ::-1].T if end == "<" else samples.T
        flat = planes.reshape(-1).astype(np.uint8)
        out.append(np.diff(np.concatenate([[0], flat]).astype(np.int16)).astype(np.uint8))
    return bytes(np.concatenate(out).tobytes())


HEIGHTS = np.array([[10.5, 11.0, 11.5], [12.0, 12.5, 13.0]], dtype="<f4")


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
