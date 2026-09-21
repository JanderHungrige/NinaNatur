"""Writing the theme's generated half (doc 97).

Two files, each a derivation of his file and of nothing else:

- `symbols.ts` — his images and his fills as SVG markup.
  Provenance: Warren Davison (Draft Sketch).
- `rules.ts` — what his symbols draw along a shape (ink, rims, shadows,
  corners, centres) as data the plan draws per shape.
  Provenance: adapted from Draft Sketch.

Markup rather than JSX: the patterns hold about a thousand elements, which the
browser parses from one string at once and React would build one by one on
every plan it mounts. Every number is written to the millimetre, so a run
writes the same bytes as the last.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

MARKS = "Warren Davison (Draft Sketch)"
ADAPTED = "adapted from Draft Sketch"
_ID = re.compile(r"^ds-[a-z0-9-]+$")
_COLOUR = re.compile(r"^#[0-9a-f]{6}$")
_PATH = re.compile(r"^[MLHVZ0-9 .-]+$")


def number(value: float) -> str:
    """To the millimetre, without trailing zeros; never "-0"."""
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


@dataclass(frozen=True)
class Mark:
    """One of his images in a tile, centred on (x, y): metres, y down as SVG runs."""
    image: str
    x: float
    y: float
    width: float
    height: float
    #: Degrees, clockwise as SVG turns.
    rotation: float = 0.0
    #: His colour through the image's alpha; None draws the image as it is.
    tint: str | None = None
    opacity: float = 1.0


@dataclass(frozen=True)
class Ring:
    x: float
    y: float
    r: float
    width: float
    colour: str
    opacity: float = 1.0


@dataclass(frozen=True)
class Lines:
    """Parallel lines across a tile, as one path."""
    d: str
    width: float
    colour: str
    opacity: float = 1.0


@dataclass(frozen=True)
class Paper:
    """His texture across the whole tile, repeating every `width` by `height`."""
    image: str
    width: float
    height: float
    tint: str | None = None
    opacity: float = 1.0


@dataclass(frozen=True)
class Sheet:
    """Small marks on a small tile of their own, repeating across the big one."""
    width: float
    height: float
    pieces: tuple[Mark | Ring, ...]


Piece = Mark | Ring | Lines | Paper | Sheet


@dataclass(frozen=True)
class Pattern:
    id: str
    width: float
    height: float
    base: str | None = None
    base_opacity: float = 1.0
    #: Bottom first, as they are painted.
    pieces: tuple[Piece, ...] = ()


@dataclass(frozen=True)
class Stop:
    offset: float
    colour: str
    opacity: float


@dataclass(frozen=True)
class Gradient:
    """A colour ramp over a whole shape, in its bounding box."""
    id: str
    radial: bool
    stops: tuple[Stop, ...]
    #: A linear ramp's ends, in the bounding box.
    ends: tuple[float, float, float, float] = (0.0, 0.5, 1.0, 0.5)


def _checked(value: str, pattern: re.Pattern[str]) -> str:
    """Nothing reaches the markup that is not an id or a colour this module made."""
    if not pattern.match(value):
        raise ValueError(f"refused in markup: {value!r}")
    return value


def variable(key: str) -> str:
    return _checked(key, _ID).replace("-", "_")


def _opacity(name: str, value: float) -> str:
    return "" if value >= 1 else f' {name}="{number(value)}"'


def _mark(mark: Mark) -> str:
    left, top = mark.x - mark.width / 2, mark.y - mark.height / 2
    box = (f'x="{number(left)}" y="{number(top)}" '
           f'width="{number(mark.width)}" height="{number(mark.height)}"')
    turn = "" if mark.rotation % 360 == 0 else (
        f' transform="rotate({number(mark.rotation)} {number(mark.x)} {number(mark.y)})"')
    if mark.tint is None:
        return (f'<image href="${{{variable(mark.image)}}}" {box} preserveAspectRatio="none"'
                f'{_opacity("opacity", mark.opacity)}{turn}/>')
    return (f'<rect {box} fill="{_checked(mark.tint, _COLOUR)}"'
            f'{_opacity("fill-opacity", mark.opacity)} mask="url(#{mark.image}-mask)"{turn}/>')


def _paper(pattern: Pattern, paper: Paper) -> tuple[list[str], str]:
    """The texture as its own pattern, and — to tint it — a mask the size of the
    tile: one fill, where copies side by side would leave hairline seams."""
    texture = f"{pattern.id}-paper"
    tile = f'width="{number(pattern.width)}" height="{number(pattern.height)}"'
    size = f'width="{number(paper.width)}" height="{number(paper.height)}"'
    image = f'<image href="${{{variable(paper.image)}}}" {size} preserveAspectRatio="none"/>'
    defs = [f'<pattern id="{texture}" {size} patternUnits="userSpaceOnUse">{image}</pattern>']
    if paper.tint is None:
        return defs, f'<rect {tile} fill="url(#{texture})"{_opacity("opacity", paper.opacity)}/>'
    defs.append(f'<mask id="{texture}-mask" maskUnits="userSpaceOnUse" x="0" y="0" {tile} '
                f'mask-type="alpha"><rect {tile} fill="url(#{texture})"/></mask>')
    return defs, (f'<rect {tile} fill="{_checked(paper.tint, _COLOUR)}"'
                  f'{_opacity("fill-opacity", paper.opacity)} mask="url(#{texture}-mask)"/>')


def _piece(piece: Piece) -> str:
    if isinstance(piece, Mark):
        return _mark(piece)
    if isinstance(piece, Ring):
        line = f'stroke-width="{number(piece.width)}"{_opacity("stroke-opacity", piece.opacity)}'
        return (f'<circle cx="{number(piece.x)}" cy="{number(piece.y)}" r="{number(piece.r)}" '
                f'fill="none" stroke="{_checked(piece.colour, _COLOUR)}" {line}/>')
    if isinstance(piece, Paper | Sheet):
        raise TypeError("a texture or a sheet is laid by its pattern")
    ink = _checked(piece.colour, _COLOUR)
    return (f'<path d="{_checked(piece.d, _PATH)}" fill="none" stroke="{ink}" '
            f'stroke-width="{number(piece.width)}"{_opacity("stroke-opacity", piece.opacity)}/>')


def _pattern(pattern: Pattern) -> list[str]:
    """The tile, drawn once, and the pattern shapes are filled with: one rect
    holding the drawn tile. A browser records a pattern's content again for
    every shape it fills, and a pattern used inside it — by that one rect —
    once: so a hundred lawns record a hundred rects, not six thousand marks."""
    size = f'width="{number(pattern.width)}" height="{number(pattern.height)}"'
    tile = f"{_checked(pattern.id, _ID)}-tile"
    defs: list[str] = []
    lines = [f'<pattern id="{tile}" {size} patternUnits="userSpaceOnUse">']
    if pattern.base is not None:
        lines.append(f'<rect {size} fill="{_checked(pattern.base, _COLOUR)}"'
                     f'{_opacity("fill-opacity", pattern.base_opacity)}/>')
    for index, piece in enumerate(pattern.pieces):
        if isinstance(piece, Paper):
            before, drawn = _paper(pattern, piece)
            defs += before
            lines.append(drawn)
        elif isinstance(piece, Sheet):
            sheet = f"{pattern.id}-sheet-{index}"
            defs += [f'<pattern id="{sheet}" width="{number(piece.width)}" '
                     f'height="{number(piece.height)}" patternUnits="userSpaceOnUse">',
                     *(_piece(mark) for mark in piece.pieces), "</pattern>"]
            lines.append(f'<rect {size} fill="url(#{sheet})"/>')
        else:
            lines.append(_piece(piece))
    return [*defs, *lines, "</pattern>",
            f'<pattern id="{pattern.id}" {size} patternUnits="userSpaceOnUse">'
            f'<rect {size} fill="url(#{tile})"/></pattern>']


def _gradient(gradient: Gradient) -> list[str]:
    tag = "radialGradient" if gradient.radial else "linearGradient"
    x1, y1, x2, y2 = gradient.ends
    where = ('cx="0.5" cy="0.5" r="0.5"' if gradient.radial else
             f'x1="{number(x1)}" y1="{number(y1)}" x2="{number(x2)}" y2="{number(y2)}"')
    stops = [f'<stop offset="{number(s.offset)}" stop-color="{_checked(s.colour, _COLOUR)}"'
             f'{_opacity("stop-opacity", s.opacity)}/>' for s in gradient.stops]
    return [f'<{tag} id="{_checked(gradient.id, _ID)}" {where}>', *stops, f"</{tag}>"]


def _mask(key: str) -> str:
    return (f'<mask id="{key}-mask" maskContentUnits="objectBoundingBox" mask-type="alpha">'
            f'<image href="${{{variable(key)}}}" width="1" height="1" preserveAspectRatio="none"/>'
            "</mask>")


def _marks(pieces: Iterable[Piece]) -> Iterator[Mark]:
    """Every mark in a tile, those on its sheets included."""
    for piece in pieces:
        if isinstance(piece, Mark):
            yield piece
        elif isinstance(piece, Sheet):
            yield from (mark for mark in piece.pieces if isinstance(mark, Mark))


def _header(provenance: str, stylx_sha256: str, about: str) -> list[str]:
    return [
        "/**",
        f" * Provenance: {provenance}",
        " *",
        f" * Generated from Draft_Sketch.stylx (sha256 {stylx_sha256[:8]}…) by",
        " * `python -m scripts.stylx_to_theme`. Do not edit: regenerate (doc 97).",
        " *",
        *(f" * {line}" if line else " *" for line in about.splitlines()),
        " */",
    ]


def symbols_file(patterns: Iterable[Pattern], gradients: Iterable[Gradient],
                 images: Mapping[str, str], stylx_sha256: str, masks: Iterable[str] = ()) -> str:
    """His images, a mask per image drawn through a tint, his patterns and ramps."""
    patterns, gradients = list(patterns), list(gradients)
    masked = set(masks) | {mark.image for pattern in patterns for mark in _marks(pattern.pieces)
                           if mark.tint is not None}
    out = _header(MARKS, stylx_sha256, (
        "His images, each once and unchanged, and his symbols' fills as SVG\n"
        "patterns. A tint is his colour through the image's alpha: what tinting\n"
        "does to the white washes and black marks he tints."))
    out += [f"import {variable(key)} from './{path}';" for key, path in sorted(images.items())]
    out += ["", "/** Every image the patterns draw, for whoever must wait for them to load. */",
            "export const IMAGES: readonly string[] = [",
            *(f"  {variable(key)}," for key in sorted(images)), "];", "",
            "/** His images by key, for marks laid along a line (doc 98). */",
            "export const IMAGE: Readonly<Record<string, string>> = {",
            *(f"  '{key}': {variable(key)}," for key in sorted(images)), "};", "",
            "/** His marks as markup: parsed by the browser in one go (see ../Defs.tsx). */",
            "export const SYMBOLS = `"]
    out += [_mask(key) for key in sorted(masked)]
    for gradient in gradients:
        out += _gradient(gradient)
    for pattern in patterns:
        out += _pattern(pattern)
    return "\n".join([*out, "`;", ""])


def rules_file(overlays: Mapping[str, list[dict[str, Any]]], stylx_sha256: str) -> str:
    """What each symbol draws along a shape, bottom first, in metres."""
    out = _header(ADAPTED, stylx_sha256, (
        "What his symbols draw along a shape rather than inside it — ink, rims,\n"
        "drop shadows, corners, centres — bottom first, in metres at 1:250. His\n"
        "scanned strokes become solid ones carrying the same ink (doc 97)."))
    body = json.dumps(overlays, indent=2, ensure_ascii=False)
    out += ["import type { Overlay } from '../overlays';", "",
            f"export const OVERLAYS: Readonly<Record<string, readonly Overlay[]>> = {body};", ""]
    return "\n".join(out)


__all__ = ["ADAPTED", "MARKS", "Gradient", "Lines", "Mark", "Paper", "Pattern", "Piece", "Ring",
           "Sheet", "Stop", "number", "rules_file", "symbols_file", "variable"]
