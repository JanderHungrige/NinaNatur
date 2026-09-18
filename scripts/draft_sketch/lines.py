"""His line symbols, laid along our fences and walls (doc 98).

A fence or a wall on the plan is an element with an outline, often drawn along
a line of its own. His Wood Fence and Brick Wall are line symbols (CIM class
4): strokes, marks every few points, splotches of varying size, caps at the
ends. Each layer becomes an overlay laid along the element's line when the
plan is drawn, bottom first:

    line-ink    a stroke along the line, or moved off it to one side
    line-marks  one of his images every few points, turned with the line
    line-boxes  a small square every few points (his fence's posts)
    line-ends   one of his images at each end

Distances are his, in metres at the reference scale: his wall's two faces
stand 0.7 m apart. The plan fits them to a wall's real faces when it draws
them (`drawAlong.tsx`) — the adaptation, named there.
"""
from __future__ import annotations

from scripts.draft_sketch.cim import Layer
from scripts.draft_sketch.outline import Overlay, metres, wave_json
from scripts.draft_sketch.tiles import Images


def _stroke(layer: Layer, images: Images) -> Overlay:
    share = images.coverage(layer.image) if layer.image else 1.0
    return {"kind": "line-ink",
            "colour": images.ink(layer.image, layer.colour) if layer.image else layer.colour.hex,
            "opacity": layer.colour.opacity, "width": metres(layer.width_pt * share),
            "offset": metres(layer.offset_pt), "wave": wave_json(layer.wave)}


def _mark(layer: Layer, images: Images, masks: set[str]) -> Overlay:
    """His image, and how it sits: turned `rotation` degrees from the line
    (counter-clockwise, as CIM turns), `width` along its own long side."""
    key = images.ship(layer.image)
    masks.add(key)
    height = layer.size_pt
    return {"mask": f"{key}-mask", "image": key, "colour": images.ink(layer.image, layer.colour),
            "opacity": layer.colour.opacity, "width": metres(height * images.aspect(layer.image)),
            "height": metres(height), "rotation": layer.rotation}


def _marks(layer: Layer, images: Images, masks: set[str]) -> Overlay:
    varied = {"sizes": list(layer.sizes)} if layer.sizes else {}
    strays = {"jitter": metres(layer.jitter_pt)} if layer.jitter_pt else {}
    return {"kind": "line-marks", **_mark(layer, images, masks),
            "spacing": metres(layer.step_pt[0]), "start": metres(layer.start_pt),
            "seed": layer.seed, **varied, **strays}


def line_overlays_of(symbol_id: str, layers: list[Layer], images: Images,
                     ) -> tuple[list[Overlay], set[str]]:
    """The line symbol's overlays bottom first, and the images drawn through a mask."""
    drawn: list[Overlay] = []
    masks: set[str] = set()
    for layer in reversed(layers):
        if layer.kind == "stroke":
            drawn.append(_stroke(layer, images))
        elif layer.kind == "along":
            drawn.append(_marks(layer, images, masks))
        elif layer.kind == "ends":
            drawn.append({"kind": "line-ends", **_mark(layer, images, masks)})
        elif layer.kind == "boxes":
            drawn.append({"kind": "line-boxes", "colour": layer.colour.hex,
                          "opacity": layer.colour.opacity, "size": metres(layer.size_pt),
                          "spacing": metres(layer.step_pt[0]), "start": metres(layer.start_pt)})
        else:
            raise ValueError(f"{symbol_id}: a line symbol's {layer.kind} layer is not drawn")
    return drawn, masks


__all__ = ["line_overlays_of"]
