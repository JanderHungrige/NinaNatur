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

from ninanatur.geo.tiff_codec import lzw, undo_predictor

#: Tags that matter here. Everything else in the directory is skipped.
_WIDTH, _HEIGHT, _BITS, _COMPRESSION = 256, 257, 258, 259
_STRIP_OFFSETS, _SAMPLES_PER_PIXEL, _STRIP_BYTES = 273, 277, 279
_TILE_WIDTH, _TILE_LENGTH, _TILE_OFFSETS, _TILE_BYTES = 322, 323, 324, 325
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
    data = _unwrap(data)
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


def _unwrap(data: bytes) -> bytes:
    """Pull the image out of a multipart WCS response, if that is what this is.

    WCS 2.0 lets a server package the coverage as `multipart/related`: a GML
    part describing the grid, then the pixels. Five of the six services in the
    registry hand back a bare GeoTIFF for `FORMAT=image/tiff`; Sachsen-Anhalt
    packages it, and is entitled to.

    Found by the TIFF magic rather than by parsing MIME headers, because the
    part boundary and the header casing vary between servers while `II*\0` and
    `MM\0*` do not.
    """
    if data[:2] in (b"II", b"MM"):
        return data
    little = data.find(b"II*\x00")
    big = data.find(b"MM\x00*")
    starts = [i for i in (little, big) if i > 0]
    if not starts:
        return data
    return data[min(starts) :]


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
    if _TILE_OFFSETS in fields:
        return _tiles(data, end, fields, width, height, bits)
    compression = _one(fields, _COMPRESSION, 1)
    if compression not in (1, 5):
        raise TiffError(f"compression {compression} is not supported")
    offsets = _array(data, end, fields, _STRIP_OFFSETS)
    counts = _array(data, end, fields, _STRIP_BYTES)
    out = bytearray()
    for offset, length in zip(offsets, counts, strict=True):
        chunk = data[offset : offset + length]
        if compression == 5:
            chunk = lzw(chunk)
            chunk = undo_predictor(chunk, end, width, _one(fields, _PREDICTOR, 1), bits)
        out += chunk
    return bytes(out)


def _tiles(
    data: bytes, end: str, fields: dict[int, _Field], width: int, height: int, bits: int
) -> bytes:
    """Reassemble a tiled image into rows.

    A tiled TIFF stores square blocks rather than horizontal strips, and pads
    each one out to a whole tile — so the last column and the last row carry
    pixels that are not in the image and must be dropped rather than shifted in.
    Sachsen-Anhalt returns 128×128 tiles for a 200×200 window: four tiles, of
    which more than half is padding.

    The same layout is what makes a Cloud-Optimised GeoTIFF, which the BKG's own
    documentation says these products may be delivered as — so this is the
    format to expect more of, not less.
    """
    compression = _one(fields, _COMPRESSION, 1)
    if compression not in (1, 5):
        raise TiffError(f"compression {compression} is not supported")
    tile_w = _one(fields, _TILE_WIDTH)
    tile_h = _one(fields, _TILE_LENGTH)
    across = (width + tile_w - 1) // tile_w
    per_sample = bits // 8

    offsets = _array(data, end, fields, _TILE_OFFSETS)
    counts = _array(data, end, fields, _TILE_BYTES)
    rows: list[bytearray] = [bytearray(width * per_sample) for _ in range(height)]
    for index, (offset, length) in enumerate(zip(offsets, counts, strict=True)):
        chunk = data[offset : offset + length]
        if compression == 5:
            chunk = lzw(chunk)
            chunk = undo_predictor(chunk, end, tile_w, _one(fields, _PREDICTOR, 1), bits)
        left = (index % across) * tile_w
        top = (index // across) * tile_h
        for line in range(tile_h):
            y = top + line
            if y >= height:
                break
            keep = min(tile_w, width - left) * per_sample
            start = line * tile_w * per_sample
            rows[y][left * per_sample : left * per_sample + keep] = chunk[start : start + keep]
    return b"".join(bytes(r) for r in rows)


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


__all__ = ["NO_DATA", "Raster", "TiffError", "read_raster"]
