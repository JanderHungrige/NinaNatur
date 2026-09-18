"""A symbol's layers, as the theme can draw them (docs 97, 98).

A symbol is a list of layers, top first, and every layer is reduced here to
what the theme can draw of it — a `Layer` of one of these kinds:

    stroke    a line along the outline (solid, or his scanned ink strip)
    fill      a flat colour, or — moved — a drop shadow
    gradient  a colour ramp across or into the shape
    paper     a tinted texture tiled over the shape (a picture fill)
    scatter   one of his images strewn at random inside the shape
    grains    a small drawn mark strewn the same way
    hatch     parallel lines across the shape
    centre    one image at the shape's centre
    vertices  one image on every corner
    along     one image every few points along the outline, or a line
    ends      one image at each end of a line
    boxes     a small square every few points along a line

Anything else is refused by name rather than skipped: a layer this does not
understand is a part of his drawing that would silently go missing.
"""
from __future__ import annotations

from dataclasses import replace

from scripts.draft_sketch.cim import (
    JSON,
    Colour,
    Layer,
    colour,
    effects_of,
    picture,
    scale_of,
    wave_of,
)

_PLACEMENTS = {
    "CIMMarkerPlacementInsidePolygon": "scatter",
    "CIMMarkerPlacementPolygonCenter": "centre",
    "CIMMarkerPlacementOnVertices": "vertices",
    "CIMMarkerPlacementAlongLineSameSize": "along",
    "CIMMarkerPlacementAlongLineVariableSize": "along",
    "CIMMarkerPlacementAtExtremities": "ends",
}



def _sizes(place: JSON) -> tuple[float, ...]:
    """His variable sizes: `numberOfSizes` steps from `minZoom` to `maxZoom`,
    rising and falling again, or in a seeded random order."""
    if place["type"] != "CIMMarkerPlacementAlongLineVariableSize":
        return ()
    count, low, high = int(place["numberOfSizes"]), float(place["minZoom"]), float(place["maxZoom"])
    steps = [low + (high - low) * i / max(1, count - 1) for i in range(count)]
    if place["variationMethod"] == "IncreasingThenDecreasing":
        steps += steps[-2:0:-1]
    elif place["variationMethod"] != "Random":
        raise ValueError(f"unknown size variation {place['variationMethod']}")
    return tuple(round(step, 4) for step in steps)


def _stroke(layer: JSON, effects: dict[str, JSON]) -> Layer:
    scanned = layer["type"] == "CIMPictureStroke"
    dashes = effects.get("Dashes", {}).get("dashTemplate", [])
    return Layer(
        "stroke",
        colour=colour(layer["tintColor"] if scanned else layer["color"]),
        width_pt=float(layer["width"]),
        wave=wave_of(effects),
        offset_pt=float(effects.get("Offset", {}).get("offset", 0.0)),
        dashes_pt=tuple(float(d) for d in dashes),
        image=picture(layer) if scanned else b"",
        scale=scale_of(effects),
    )


def _marker(layer: JSON) -> Layer:
    place = layer["markerPlacement"]
    kind = _PLACEMENTS.get(place["type"])
    if kind is None:
        raise ValueError(f"unknown marker placement {place['type']}")
    if kind == "along":
        # One mark every `placementTemplate[0]` points, `offset` off the line.
        step = (float((place.get("placementTemplate") or [0.0])[0]), 0.0)
    else:
        step = (float(place.get("stepX", 0.0)), float(place.get("stepY", 0.0)))
    placed = Layer(
        kind,
        size_pt=float(layer["size"]),
        rotation=float(layer.get("rotation", 0.0)),
        step_pt=step,
        offset_pt=float(place.get("offset", 0.0)) if kind == "along" else 0.0,
        seed=int(place.get("seed", 0)),
        randomness=float(place.get("randomness", 0.0)) / 100,
        scale=scale_of(effects_of(layer)),
        sizes=_sizes(place),
        method=str(place.get("variationMethod", "")),
        start_pt=float(place.get("offsetAlongLine", 0.0)),
        jitter_pt=float(place.get("maxRandomOffset", 0.0)),
    )
    if layer["type"] == "CIMPictureMarker":
        return replace(placed, colour=colour(layer["tintColor"]), image=picture(layer))
    if kind == "along":
        return replace(placed, kind="boxes", colour=_box(layer))
    if kind != "scatter":
        raise ValueError("a vector marker anywhere but strewn inside or along a line")
    ink, share = _grain(layer)
    return replace(placed, kind="grains", colour=ink, width_pt=share * placed.size_pt)


def _box(layer: JSON) -> Colour:
    """A vector marker along a line, understood only as what he draws with it:
    a square filling its frame. Returns its fill."""
    (graphic,) = layer["markerGraphics"]
    frame = layer["frame"]
    corners = {(frame["xmin"], frame["ymin"]), (frame["xmax"], frame["ymax"])}
    rings = graphic["geometry"].get("rings") or [[]]
    if len(rings) != 1 or not corners <= {tuple(point) for point in rings[0]}:
        raise ValueError("a vector marker along a line that is not a square")
    fill = next(s for s in graphic["symbol"]["symbolLayers"] if s["type"] == "CIMSolidFill")
    return colour(fill["color"])


def _grain(layer: JSON) -> tuple[Colour, float]:
    """A vector marker, understood only as what he draws with it: a ring as wide
    as the marker. Returns its line's colour, and its width as a share of the
    marker's size — which is how it scales, when symbols scale proportionally."""
    (graphic,) = layer["markerGraphics"]
    rings = graphic["geometry"].get("curveRings")
    if not rings or len(rings) != 1 or len(rings[0]) != 2 or "a" not in rings[0][1]:
        raise ValueError("a vector marker that is not one circle")
    if not layer.get("scaleSymbolsProportionally", False):
        raise ValueError("a vector marker whose line does not scale with it")
    frame = layer["frame"]
    across = float(frame["xmax"]) - float(frame["xmin"])
    line = next(s for s in graphic["symbol"]["symbolLayers"] if s["type"] == "CIMSolidStroke")
    return colour(line["color"]), float(line["width"]) / across


def _hatch(layer: JSON) -> Layer:
    line = next(s for s in layer["lineSymbol"]["symbolLayers"] if s.get("enable", True))
    ink = _stroke(line, effects_of(line))
    return Layer(
        "hatch", colour=ink.colour, width_pt=ink.width_pt, image=ink.image,
        separation_pt=float(layer["separation"]), rotation=float(layer.get("rotation", 0.0)),
        shift_pt=float(layer.get("offsetY", 0.0)),
    )


def _gradient(layer: JSON, effects: dict[str, JSON]) -> Layer:
    ramp = layer["colorRamp"]
    if ramp["type"] != "CIMPolarContinuousColorRamp":
        raise ValueError(f"unknown colour ramp {ramp['type']}")
    return Layer(
        "gradient", ramp=(colour(ramp["fromColor"]), colour(ramp["toColor"])),
        method=str(layer["gradientMethod"]), angle=float(layer.get("angle", 0.0)),
        size_pt=float(layer.get("gradientSize", 0.0)), wave=wave_of(effects),
    )


def _layer(layer: JSON) -> Layer:
    kind, effects = layer["type"], effects_of(layer)
    if kind in ("CIMSolidStroke", "CIMPictureStroke"):
        return _stroke(layer, effects)
    if kind == "CIMSolidFill":
        move = effects.get("Move", {})
        return Layer(
            "fill", colour=colour(layer["color"]), wave=wave_of(effects),
            move_pt=(float(move.get("offsetX", 0.0)), float(move.get("offsetY", 0.0))),
        )
    if kind == "CIMPictureFill":
        return Layer("paper", colour=colour(layer["tintColor"]), image=picture(layer),
                     size_pt=float(layer["height"]), rotation=float(layer.get("rotation", 0.0)))
    if kind in ("CIMPictureMarker", "CIMVectorMarker"):
        return _marker(layer)
    if kind == "CIMHatchFill":
        return _hatch(layer)
    if kind == "CIMGradientFill":
        return _gradient(layer, effects)
    raise ValueError(f"a layer this converter does not draw: {kind}")


def layers_of(symbol: JSON) -> list[Layer]:
    """The symbol's layers that are switched on, top first as CIM lists them."""
    return [_layer(layer) for layer in symbol["symbolLayers"] if layer.get("enable", True)]


__all__ = ["layers_of"]
