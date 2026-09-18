"""Reading Draft Sketch's images — standard library only (doc 97).

The theme ships his images unchanged, one copy each, and tints them in SVG: his
colour through the image's alpha. So the converter only has to know a few
things about an image — its size, how much of it is painted, and whether it is
a white wash to be tinted or an ink mark to be drawn as it is. All of them need
the pixels, which means reading PNG.

His images are 8-bit RGBA, not interlaced; that is what this reads, and it
refuses anything else rather than guessing. A dependency would have done this
in one line — but the project's Python dependencies are pinned by hash since
Wave 20, and a converter run by hand is not reason enough to widen what CI
installs.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

SIGNATURE = b"\x89PNG\r\n\x1a\n"
_CHANNELS = {2: 3, 6: 4}
#: Above this mean brightness an image is a wash: white, to be tinted.
WHITE = 0.8


@dataclass(frozen=True)
class Image:
    width: int
    height: int
    #: Row-major, four bytes a pixel.
    rgba: bytes


def _paeth(left: int, up: int, upleft: int) -> int:
    guess = left + up - upleft
    to_left, to_up, to_upleft = abs(guess - left), abs(guess - up), abs(guess - upleft)
    if to_left <= to_up and to_left <= to_upleft:
        return left
    return up if to_up <= to_upleft else upleft


def _unfilter(kind: int, line: bytearray, previous: bytes, bpp: int) -> None:
    for i in range(len(line)):
        left = line[i - bpp] if i >= bpp else 0
        up = previous[i]
        upleft = previous[i - bpp] if i >= bpp else 0
        if kind == 1:
            line[i] = (line[i] + left) & 0xFF
        elif kind == 2:
            line[i] = (line[i] + up) & 0xFF
        elif kind == 3:
            line[i] = (line[i] + (left + up) // 2) & 0xFF
        elif kind == 4:
            line[i] = (line[i] + _paeth(left, up, upleft)) & 0xFF
        elif kind != 0:
            raise ValueError(f"unknown PNG row filter {kind}")


def _chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    if not data.startswith(SIGNATURE):
        raise ValueError("not a PNG")
    found: list[tuple[bytes, bytes]] = []
    at = len(SIGNATURE)
    while at < len(data):
        (length,) = struct.unpack(">I", data[at:at + 4])
        found.append((data[at + 4:at + 8], data[at + 8:at + 8 + length]))
        at += 12 + length
    return found


def dimensions(data: bytes) -> tuple[int, int]:
    """Width and height, from the header alone."""
    header = next(body for kind, body in _chunks(data) if kind == b"IHDR")
    width, height = struct.unpack(">II", header[:8])
    return int(width), int(height)


def decode(data: bytes) -> Image:
    """8-bit RGB or RGBA, not interlaced; anything else is refused."""
    chunks = _chunks(data)
    header = next(body for kind, body in chunks if kind == b"IHDR")
    width, height, depth, colour, _method, _filtering, interlace = struct.unpack(">IIBBBBB", header)
    if depth != 8 or colour not in _CHANNELS or interlace:
        raise ValueError(
            f"unsupported PNG: depth {depth}, colour type {colour}, interlace {interlace}")
    channels = _CHANNELS[colour]
    raw = zlib.decompress(b"".join(body for kind, body in chunks if kind == b"IDAT"))
    stride = width * channels
    out = bytearray()
    previous = bytes(stride)
    for row in range(height):
        start = row * (stride + 1)
        line = bytearray(raw[start + 1:start + 1 + stride])
        _unfilter(raw[start], line, previous, channels)
        out.extend(line)
        previous = bytes(line)
    if channels == 3:
        out = bytearray(b"".join(bytes(out[i:i + 3]) + b"\xff" for i in range(0, len(out), 3)))
    return Image(width, height, bytes(out))


def brightness(image: Image) -> float:
    """Mean brightness of what is painted, 0 black to 1 white, weighted by alpha."""
    painted = weight = 0.0
    px = image.rgba
    for i in range(0, len(px), 4):
        alpha = px[i + 3] / 255
        painted += alpha * (0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]) / 255
        weight += alpha
    return painted / weight if weight else 1.0


def is_wash(image: Image) -> bool:
    """A white wash, tinted by the symbol that uses it — rather than an ink mark."""
    return brightness(image) >= WHITE


def coverage(image: Image) -> float:
    """How much of the image is painted: its mean alpha, 0 to 1. A scanned
    stroke of his is ragged; this is how much ink it lays down."""
    alpha = image.rgba[3::4]
    return sum(alpha) / (255 * len(alpha)) if alpha else 0.0


__all__ = ["WHITE", "Image", "brightness", "coverage", "decode", "dimensions", "is_wash"]
