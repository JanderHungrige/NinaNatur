"""Just enough GeoTIFF to read a height raster.

Six services, three disagreements. Brandenburg, Mecklenburg-Vorpommern and
Hessen return uncompressed little-endian 32-bit float; Nordrhein-Westfalen and
Niedersachsen return the same thing LZW-compressed; Baden-Württemberg returns
**big-endian 16-bit unsigned integers**. Read with the wrong assumption, the last
of those yields heights in the millions — which is the good case, because it is
obviously wrong. The bad case is a subtler one silently off.

A library would cover all of it. GDAL is a hundred megabytes of wheel and
`tifffile` pulls in more than this needs; the reader below is the fraction of
TIFF 6.0 that these six services actually emit, and it refuses the rest loudly
rather than guessing.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

import numpy as np

#: Tags that matter here. Everything else in the directory is skipped.
_WIDTH, _HEIGHT, _BITS, _COMPRESSION = 256, 257, 258, 259
_STRIP_OFFSETS, _SAMPLES_PER_PIXEL, _STRIP_BYTES = 273, 277, 279
_PREDICTOR, _SAMPLE_FORMAT = 317, 339

#: Byte width of each TIFF field type, indexed by its type code.
_TYPE_BYTES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}
_TYPE_CODE = {1: "B", 3: "H", 4: "I"}

NO_DATA = -9999.0


class TiffError(ValueError):
    """A file this reader will not guess at."""


@dataclass(frozen=True)
class Raster:
    """A height grid as it came off the wire, row-major from the top-left."""

    width: int
    height: int
    #: Metres above the height reference. NoData is kept as NaN rather than as
    #: -9999: border tiles and water genuinely have none, and a -9999 averaged
    #: into a slope is a cliff that is not there.
    values: np.ndarray


def read_raster(data: bytes) -> Raster:
    """Decode a single-band TIFF into metres.

    Raises rather than guesses. A service that starts returning tiles, or JPEG,
    or three bands, is a change worth being told about at the moment it happens.
    """
    if data[:2] == b"II":
        end = "<"
    elif data[:2] == b"MM":
        end = ">"
    else:
        raise TiffError(f"not a TIFF: starts {data[:8]!r}")

    fields = _directory(data, end)
    width, height = _one(fields, _WIDTH), _one(fields, _HEIGHT)
    bits = _one(fields, _BITS, 8)
    sample_format = _one(fields, _SAMPLE_FORMAT, 1)
    if _one(fields, _SAMPLES_PER_PIXEL, 1) != 1:
        raise TiffError("only single-band rasters are supported")

    raw = _strips(data, end, fields, width, height, bits)
    values = _to_metres(raw, end, bits, sample_format)
    if values.size != width * height:
        raise TiffError(f"{values.size} values for a {width}x{height} raster")
    grid = values.reshape(height, width).astype(np.float64)
    grid[grid <= NO_DATA] = np.nan
    return Raster(width=width, height=height, values=grid)


@dataclass(frozen=True)
class _Field:
    """One directory entry: its type, how many of them, and where they live."""

    kind: int
    count: int
    #: The value itself when it fits in the four-byte field, otherwise the
    #: offset to where the values are.
    at: int


def _directory(data: bytes, end: str) -> dict[int, _Field]:
    """The first image file directory.

    Big-endian stores a short inline **left**-justified in the four-byte value
    field, so the type has to be read before the value — the mistake that made
    Baden-Württemberg look like a 13-million-pixel image.
    """
    offset = struct.unpack_from(end + "I", data, 4)[0]
    entries = struct.unpack_from(end + "H", data, offset)[0]
    fields: dict[int, _Field] = {}
    for i in range(entries):
        at = offset + 2 + i * 12
        tag, kind, count = struct.unpack_from(end + "HHI", data, at)
        if _TYPE_BYTES.get(kind, 4) * count <= 4 and kind in _TYPE_CODE:
            value = struct.unpack_from(end + _TYPE_CODE[kind], data, at + 8)[0]
        else:
            value = struct.unpack_from(end + "I", data, at + 8)[0]
        fields[tag] = _Field(kind=kind, count=count, at=value)
    return fields


def _one(fields: dict[int, _Field], tag: int, default: int | None = None) -> int:
    field = fields.get(tag)
    if field is None:
        if default is None:
            raise TiffError(f"tag {tag} is missing")
        return default
    return field.at


def _array(data: bytes, end: str, fields: dict[int, _Field], tag: int) -> list[int]:
    """A strip array, read with **its own** field type.

    Not a detail: Brandenburg stores the strip offsets as LONG and the strip
    byte counts as SHORT in the same file. Reading both as LONG produced
    plausible-looking garbage lengths and a raster nine times too long.
    """
    field = fields[tag]
    if field.count == 1:
        return [field.at]
    code = _TYPE_CODE.get(field.kind)
    if code is None:
        raise TiffError(f"tag {tag} has unreadable type {field.kind}")
    return list(struct.unpack_from(end + f"{field.count}{code}", data, field.at))


def _strips(
    data: bytes, end: str, fields: dict[int, _Field], width: int, height: int, bits: int
) -> bytes:
    compression = _one(fields, _COMPRESSION, 1)
    if compression not in (1, 5):
        raise TiffError(f"compression {compression} is not supported")
    offsets = _array(data, end, fields, _STRIP_OFFSETS)
    counts = _array(data, end, fields, _STRIP_BYTES)
    out = bytearray()
    for offset, length in zip(offsets, counts, strict=True):
        chunk = data[offset : offset + length]
        if compression == 5:
            chunk = _lzw(chunk)
            chunk = _undo_predictor(
                chunk, end, _one(fields, _PREDICTOR, 1), width, bits
            )
        out += chunk
    return bytes(out)


def _to_metres(raw: bytes, end: str, bits: int, sample_format: int) -> np.ndarray:
    """Interpret the bytes as the numbers the service says they are.

    Baden-Württemberg's 16-bit unsigned values are whole metres — verified
    against Stuttgart, where they read 241 to 244. They are not a scaled
    fixed-point, which is the thing to check first the next time a service is
    added, because reading decimetres as metres is off by ten and looks
    plausible on flat ground.
    """
    if sample_format == 3 and bits == 32:
        return np.frombuffer(raw, dtype=np.dtype(end + "f4"))
    if sample_format == 3 and bits == 64:
        return np.frombuffer(raw, dtype=np.dtype(end + "f8"))
    if sample_format in (1, 0) and bits == 16:
        return np.frombuffer(raw, dtype=np.dtype(end + "u2"))
    if sample_format == 2 and bits == 16:
        return np.frombuffer(raw, dtype=np.dtype(end + "i2"))
    raise TiffError(f"{bits}-bit sample format {sample_format} is not supported")


def _lzw(data: bytes) -> bytes:
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
                raise TiffError(f"LZW code {code} outside the table")
            out += entry
            if previous:
                table.append(previous + entry[:1])
            previous = entry
            if len(table) + 1 >= (1 << width) and width < 12:
                width += 1
    return bytes(out)


def _undo_predictor(chunk: bytes, end: str, predictor: int, width: int, bits: int) -> bytes:
    """Reverse whatever differencing the encoder applied before LZW.

    There are two, they are not variations of each other, and using the wrong
    one produces a raster rather than an error. Niedersachsen uses predictor 3
    and Nordrhein-Westfalen none, on the same product from the same kind of
    service.
    """
    if predictor == 1:
        return chunk
    if predictor == 2:
        return _undo_horizontal(chunk, end, width, bits)
    if predictor == 3:
        return _undo_floating_point(chunk, end, width, bits)
    raise TiffError(f"predictor {predictor} is not supported")


def _undo_horizontal(chunk: bytes, end: str, width: int, bits: int) -> bytes:
    """Predictor 2: each sample is stored as its difference from the one left of it."""
    dtype = np.dtype(end + ("u2" if bits == 16 else "u4" if bits == 32 else "u1"))
    flat = np.frombuffer(chunk, dtype=dtype)
    usable = (flat.size // width) * width
    grid = flat[:usable].reshape(-1, width).copy()
    np.cumsum(grid, axis=1, dtype=dtype, out=grid)
    return bytes(grid.tobytes() + flat[usable:].tobytes())


def _undo_floating_point(chunk: bytes, end: str, width: int, bits: int) -> bytes:
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


__all__ = ["NO_DATA", "Raster", "TiffError", "read_raster"]
