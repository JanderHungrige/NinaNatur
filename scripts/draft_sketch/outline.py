"""What his symbols draw along a shape, as rules the plan follows per shape (doc 97).

A pattern cannot know where a shape's edge is; his ink, rims, shadows, corner
marks, centre marks and ramps all do. They become overlays: data in metres,
drawn from each shape's own outline when the plan is drawn, bottom first. What
SVG cannot do of them is dropped here, by name, where it is decided:

- a picture stroke is his scanned strip; SVG cannot lay an image along a path.
  Ink becomes a solid line as wide as the ink in the strip; a rim (a stroke
  moved inside the shape) keeps its width and becomes as faint as its strip.
- marks along the outline and on its corners are drawn as the strokes they
  are: short ticks, and edges carried on past their corners.
- a "buffered" ramp runs in from the edge by distance; SVG has no such paint.
  Its inside colour is the fill's base (see tiles), its rim is left out; so is
  a gap cut in an outline.

Where a ramp goes is read off his own style sheet, which is what his symbols
look like drawn: a linear ramp's first colour lies the way its angle points
(his trees are lit from the upper left, opposite their shadows), and a circular
one's first colour is its rim.
"""
from __future__ import annotations

import math
from typing import Any

from scripts.draft_sketch.cim import Layer, Wave
from scripts.draft_sketch.emit import Gradient, Stop
from scripts.draft_sketch.tiles import POINT_M, Images

Overlay = dict[str, Any]
#: Layers the tile holds: nothing to draw along the outline for them.
_TILED = ("paper", "scatter", "grains", "hatch")


def metres(points: float) -> float:
    """His points, as metres on the ground at the reference scale."""
    return round(points * POINT_M, 4)


def wave_json(wave: Wave | None) -> dict[str, float] | None:
    if wave is None:
        return None
    return {"amplitude": metres(wave.amplitude), "period": metres(wave.period), "seed": wave.seed}


def _scaled(layer: Layer) -> dict[str, float]:
    """His Scale effect: the outline drawn again smaller, about its middle — the
    rings inside his Tree 2. Left out where it is 1, as it nearly always is."""
    return {} if layer.scale == 1.0 else {"scale": layer.scale}


def _stroke(layer: Layer, images: Images) -> Overlay:
    share = images.coverage(layer.image) if layer.image else 1.0
    colour = images.ink(layer.image, layer.colour) if layer.image else layer.colour.hex
    opacity = layer.colour.opacity
    if layer.offset_pt > 0:
        raise ValueError("a stroke moved outside the shape")
    if layer.offset_pt < 0:
        return {"kind": "band", "colour": colour, "opacity": round(opacity * share, 3),
                "width": metres(layer.width_pt), "inset": metres(-layer.offset_pt),
                "wave": wave_json(layer.wave)}
    return {"kind": "ink", "colour": colour, "opacity": opacity,
            "width": metres(layer.width_pt * share), "wave": wave_json(layer.wave),
            "dashes": [metres(d) for d in layer.dashes_pt] or None, **_scaled(layer)}


def _ramp(gradient_id: str, layer: Layer) -> Gradient:
    """A linear or circular ramp over the shape's bounding box. His colours run
    from `fromColor` at the ramp's start — the centre of a circular one — to
    `toColor` over his share of the shape."""
    assert layer.ramp is not None
    first, last = layer.ramp
    share = layer.size_pt / 100
    if layer.method == "Circular":
        # From the middle out: his last colour there, his first at the rim.
        return Gradient(gradient_id, True, (Stop(0.0, last.hex, last.opacity),
                                            Stop(share, first.hex, first.opacity)))
    # CIM's angle turns counter-clockwise from east, with y up; a bounding box
    # has y down. The ramp starts where the angle points.
    dx, dy = math.cos(math.radians(layer.angle)) / 2, -math.sin(math.radians(layer.angle)) / 2
    ends = (round(0.5 + dx, 4), round(0.5 + dy, 4), round(0.5 - dx, 4), round(0.5 - dy, 4))
    return Gradient(gradient_id, False, (Stop(0.0, first.hex, first.opacity),
                                         Stop(share, last.hex, last.opacity)), ends)


def _centre(layer: Layer, images: Images) -> tuple[Overlay, str]:
    """His mark at the shape's centre, and the image it is drawn through."""
    key = images.ship(layer.image)
    height = layer.size_pt
    return ({"kind": "centre", "mask": f"{key}-mask",
             "colour": images.ink(layer.image, layer.colour),
             "opacity": layer.colour.opacity, "width": metres(height * images.aspect(layer.image)),
             "height": metres(height), "rotation": -layer.rotation}, key)


def _corners(layer: Layer, images: Images) -> Overlay:
    """Two of his marks cross on every corner, each along one of its edges and
    half of it past the corner: an edge drawn on past its end, as a hand does.
    Drawn as those lines — the image itself is not needed."""
    height = layer.size_pt
    return {"kind": "overshoot", "colour": images.ink(layer.image, layer.colour),
            "opacity": layer.colour.opacity, "width": metres(height * images.coverage(layer.image)),
            "length": metres(height * images.aspect(layer.image) / 2)}


def _ticks(layer: Layer, images: Images) -> Overlay:
    """His small marks every few points along the outline, at an angle to it —
    drawn as the short strokes they are. Where he varies their size, they
    swell and shrink in his order (his Tree 2's serrations)."""
    height = layer.size_pt
    varied = {"sizes": list(layer.sizes)} if layer.sizes else {}
    return {"kind": "ticks", "colour": images.ink(layer.image, layer.colour),
            "opacity": layer.colour.opacity,
            "width": metres(height * images.coverage(layer.image)),
            "length": metres(height * images.aspect(layer.image)),
            "spacing": metres(layer.step_pt[0]), "inset": metres(abs(layer.offset_pt)),
            "angle": layer.rotation, **varied, **_scaled(layer)}


def _tiled(layer: Layer) -> bool:
    """Part of the fill's tile (see tiles): nothing to draw along the outline."""
    return layer.kind in _TILED or (layer.kind == "fill" and layer.move_pt == (0.0, 0.0))


def _along(symbol_id: str, layer: Layer, images: Images, masks: set[str]) -> Overlay | None:
    """What one layer draws along the shape; None for a layer drawn elsewhere or left out."""
    if layer.kind == "fill":
        return {"kind": "shadow", "colour": layer.colour.hex, "opacity": layer.colour.opacity,
                "dx": metres(layer.move_pt[0]), "dy": metres(layer.move_pt[1]),
                "wave": wave_json(layer.wave)}
    if layer.kind == "stroke":
        return _stroke(layer, images)
    if layer.kind == "centre":
        overlay, key = _centre(layer, images)
        masks.add(key)
        return overlay
    if layer.kind == "vertices":
        return _corners(layer, images)
    if layer.kind == "along":
        return _ticks(layer, images)
    if layer.kind == "gradient":
        return None
    raise ValueError(f"{symbol_id}: nothing draws a {layer.kind} layer")


def overlays_of(symbol_id: str, layers: list[Layer], images: Images,
                ) -> tuple[list[Overlay], list[Gradient], set[str]]:
    """The symbol's overlays bottom first, the ramps they paint with, and the
    images they draw through a mask.

    A pattern cannot hold a ramp over the whole shape, so ramps are overlays,
    over the fill. One he paints under the fill's texture is followed by the
    texture again; one with the texture on both sides is refused."""
    drawn: list[Overlay] = []
    ramps: list[Gradient] = []
    masks: set[str] = set()
    redraw = False
    for index in reversed(range(len(layers))):
        layer = layers[index]
        if _tiled(layer):
            if redraw:
                drawn.append({"kind": "wash", "fill": f"url(#{symbol_id})"})
                redraw = False
            continue
        if layer.kind == "gradient" and layer.method in ("Linear", "Circular"):
            above = any(_tiled(other) for other in layers[:index])
            if above and any(_tiled(other) for other in layers[index + 1:]):
                raise ValueError(f"{symbol_id}: a fill's layers on both sides of a ramp")
            ramps.append(_ramp(f"{symbol_id}-ramp-{len(ramps)}", layer))
            drawn.append({"kind": "wash", "fill": f"url(#{ramps[-1].id})"})
            redraw = above
            continue
        overlay = _along(symbol_id, layer, images, masks)
        if overlay is not None and overlay not in drawn:
            drawn.append(overlay)
    return drawn, ramps, masks


__all__ = ["Overlay", "metres", "overlays_of", "wave_json"]
