"""TIFF files built byte by byte, for the tests that read them.

Shared by `test_tiff.py`, which checks the reader against every shape the eight
services emit, and `test_parsers_refuse.py`, which mangles them. Split out of
`test_tiff.py` when it passed three hundred lines — and one test module importing
another's helpers was the wrong seam anyway.

The LZW stream comes from an encoder written from the specification, not from
the decoder under test: encoding and decoding are different enough algorithms
that agreeing on the early-change rule is evidence rather than a shared
assumption — once a stream is long enough to cross it.
"""
from __future__ import annotations

import struct

import numpy as np


def _lzw_encode(data: bytes) -> bytes:
    """TIFF LZW, written from the spec to check the decoder against.

    Widens its codes where libtiff's encoder does — once the next free code is
    past the largest the current width can hold — clears a full table at 4094,
    and widens once more after the last code if the decoder will, before EOI.
    It widened one code early until 2026-09-11, which no test noticed because
    every stream here fitted in nine-bit codes.
    """
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
        held &= (1 << bits) - 1

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
        if nxt == 4094:
            emit(256, width)
            table = {bytes([i]): i for i in range(256)}
            nxt, width = 258, 9
        elif nxt >= (1 << width) and width < 12:
            width += 1
        current = bytes([byte])
    if current:
        emit(table[current], width)
        nxt += 1  # the decoder adds an entry for the last code too
        if nxt >= (1 << width) and width < 12:
            width += 1
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


def _tiled(values: np.ndarray, tile: int = 128, big_endian: bool = False) -> bytes:
    """A tiled TIFF, padded out to whole tiles the way the format requires."""
    end = ">" if big_endian else "<"
    height, width = values.shape
    bits = values.dtype.itemsize * 8
    across = (width + tile - 1) // tile
    down = (height + tile - 1) // tile

    blocks: list[bytes] = []
    for ty in range(down):
        for tx in range(across):
            block = np.zeros((tile, tile), dtype=values.dtype)
            rows = min(tile, height - ty * tile)
            cols = min(tile, width - tx * tile)
            block[:rows, :cols] = values[
                ty * tile : ty * tile + rows, tx * tile : tx * tile + cols
            ]
            blocks.append(block.astype(end + values.dtype.str[1:]).tobytes())

    entries = [
        (256, 3, 1, width), (257, 3, 1, height), (258, 3, 1, bits),
        (259, 3, 1, 1), (277, 3, 1, 1), (322, 3, 1, tile), (323, 3, 1, tile),
        (339, 3, 1, 3 if values.dtype.kind == "f" else 1),
    ]
    header = 8
    dir_at = header + sum(len(b) for b in blocks)
    n = len(entries) + 2
    arrays_at = dir_at + 2 + n * 12 + 4

    offsets, at = [], header
    for b in blocks:
        offsets.append(at)
        at += len(b)
    counts = [len(b) for b in blocks]

    out = bytearray(b"MM\x00\x2a" if big_endian else b"II\x2a\x00")
    out += struct.pack(end + "I", dir_at)
    for b in blocks:
        out += b

    all_entries = [*entries,
                   (324, 4, len(blocks), arrays_at),
                   (325, 4, len(blocks), arrays_at + 4 * len(blocks))]
    all_entries.sort()
    out += struct.pack(end + "H", len(all_entries))
    for tag, kind, count, value in all_entries:
        code = {1: "B", 3: "H", 4: "I"}[kind]
        raw = struct.pack(end + code, value)
        out += struct.pack(end + "HHI", tag, kind, count) + raw + b"\x00" * (4 - len(raw))
    out += struct.pack(end + "I", 0)
    out += struct.pack(end + f"{len(blocks)}I", *offsets)
    out += struct.pack(end + f"{len(blocks)}I", *counts)
    return bytes(out)


HEIGHTS = np.array([[10.5, 11.0, 11.5], [12.0, 12.5, 13.0]], dtype="<f4")
