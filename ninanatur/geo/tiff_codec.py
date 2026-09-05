"""Undoing what a TIFF encoder did before it wrote the bytes.

Split from `tiff.py` when that file crossed three hundred lines, and the seam is
a real one: `tiff.py` is about a file's layout — where the directory is, where
the strips or tiles live — while this is about the bytes inside one of them.

Two of the eight services in the registry compress, and they do not agree on how:
Nordrhein-Westfalen uses LZW with no predictor, Niedersachsen uses LZW with the
floating-point predictor. Neither is a variation of the other and using the
wrong one produces a raster rather than an error.
"""
from __future__ import annotations

import numpy as np


class TiffCodecError(ValueError):
    """A stream this decoder will not guess at."""


def lzw(data: bytes) -> bytes:
    """TIFF's LZW variant: 9-bit codes growing to 12, with the early change.

    "Early change" is the part everybody gets wrong: the width grows one code
    *before* the table is actually full, so 511 and not 512 is where nine bits
    become ten. Getting it wrong decodes the first strip and garbles the rest.
    """
    clear, end_of_information, first = 256, 257, 258
    table: list[bytes] = [bytes([i]) for i in range(256)] + [b"", b""]
    out = bytearray()
    previous = b""
    width, value, bits_held = 9, 0, 0

    for byte in data:
        value = (value << 8) | byte
        bits_held += 8
        while bits_held >= width:
            code = (value >> (bits_held - width)) & ((1 << width) - 1)
            bits_held -= width
            if code == end_of_information:
                return bytes(out)
            if code == clear:
                table = table[:first]
                width, previous = 9, b""
                continue
            if code < len(table):
                entry = table[code]
            elif code == len(table) and previous:
                entry = previous + previous[:1]
            else:
                raise TiffCodecError(f"LZW code {code} outside the table")
            out += entry
            if previous:
                table.append(previous + entry[:1])
            previous = entry
            if len(table) + 1 >= (1 << width) and width < 12:
                width += 1
    return bytes(out)


def undo_predictor(chunk: bytes, end: str, width: int, predictor: int, bits: int) -> bytes:
    """Reverse whatever differencing the encoder applied before LZW.

    There are two, they are not variations of each other, and using the wrong
    one produces a raster rather than an error. Niedersachsen uses predictor 3
    and Nordrhein-Westfalen none, on the same product from the same kind of
    service.
    """
    if predictor == 1:
        return chunk
    if predictor == 2:
        return undo_horizontal(chunk, end, width, bits)
    if predictor == 3:
        return undo_floating_point(chunk, end, width, bits)
    raise TiffCodecError(f"predictor {predictor} is not supported")


def undo_horizontal(chunk: bytes, end: str, width: int, bits: int) -> bytes:
    """Predictor 2: each sample is stored as its difference from the one left of it."""
    dtype = np.dtype(end + ("u2" if bits == 16 else "u4" if bits == 32 else "u1"))
    flat = np.frombuffer(chunk, dtype=dtype)
    usable = (flat.size // width) * width
    grid = flat[:usable].reshape(-1, width).copy()
    np.cumsum(grid, axis=1, dtype=dtype, out=grid)
    return bytes(grid.tobytes() + flat[usable:].tobytes())


def undo_floating_point(chunk: bytes, end: str, width: int, bits: int) -> bytes:
    """Predictor 3: byte-plane separation, then differencing across the bytes.

    A float's exponent barely changes between neighbouring ground heights while
    its mantissa changes completely, so the encoder splits each row into byte
    planes — every sample's most significant byte first, then the next — and
    differences *those*. It compresses far better and it is a different
    reconstruction: undo the byte-wise sum along the row, then reassemble each
    sample from one byte out of each plane, in the file's own byte order.
    """
    per_sample = bits // 8
    row_bytes = width * per_sample
    flat = np.frombuffer(chunk, dtype=np.uint8)
    rows = flat.size // row_bytes
    grid = flat[: rows * row_bytes].reshape(rows, row_bytes).copy()
    np.cumsum(grid, axis=1, dtype=np.uint8, out=grid)

    planes = grid.reshape(rows, per_sample, width)
    # Plane 0 holds the most significant byte. A little-endian file wants it
    # last in each sample, a big-endian one first.
    ordered = planes[:, ::-1, :] if end == "<" else planes
    return bytes(np.ascontiguousarray(ordered.transpose(0, 2, 1)).tobytes())


__all__ = ["TiffCodecError", "lzw", "undo_horizontal", "undo_predictor"]
