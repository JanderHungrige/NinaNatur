"""Reading his symbols: CIM 2.3 as ArcGIS Pro keeps it in a .stylx (doc 97).

A .stylx is a SQLite database whose ITEMS table holds one JSON document per
symbol, each ending in a NUL. A polygon symbol is a list of layers, top first,
and every layer is reduced here to what the theme can draw of it — a `Layer`
of one of these kinds:

    stroke    a line along the outline (solid, or his scanned ink strip)
    fill      a flat colour, or — moved — a drop shadow
    gradient  a colour ramp across or into the shape
    paper     a tinted texture tiled over the shape (a picture fill)
    scatter   one of his images strewn at random inside the shape
    grains    a small drawn mark strewn the same way
    hatch     parallel lines across the shape
    centre    one image at the shape's centre
    vertices  one image on every corner
    along     one image every few points along the outline

Anything else is refused by name rather than skipped: a layer this does not
understand is a part of his drawing that would silently go missing.
"""
from __future__ import annotations

import base64
import colorsys
import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, NamedTuple

JSON = dict[str, Any]
_PLACEMENTS = {
    "CIMMarkerPlacementInsidePolygon": "scatter",
    "CIMMarkerPlacementPolygonCenter": "centre",
    "CIMMarkerPlacementOnVertices": "vertices",
    "CIMMarkerPlacementAlongLineSameSize": "along",
}


class Colour(NamedTuple):
    hex: str
    opacity: float


@dataclass(frozen=True)
class Wave:
    """His "Random" waveform: a wander of up to `amplitude` every `period`, in points."""
    amplitude: float
    period: float
    seed: int


@dataclass(frozen=True)
class Layer:
    kind: str
    colour: Colour = Colour("#000000", 1.0)
    #: A stroke's width, or a grain's line.
    width_pt: float = 0.0
    wave: Wave | None = None
    move_pt: tuple[float, float] = (0.0, 0.0)
    #: A stroke moved off the outline; negative is inward.
    offset_pt: float = 0.0
    dashes_pt: tuple[float, ...] = ()
    #: A picture layer's PNG, exactly as he embedded it.
    image: bytes = b""
    #: A marker's height, a picture fill's tile height, a grain's diameter.
    size_pt: float = 0.0
    #: Degrees, counter-clockwise, as CIM turns.
    rotation: float = 0.0
    step_pt: tuple[float, float] = (0.0, 0.0)
    seed: int = 0
    #: A random grid's scatter, 0 to 1 of a cell.
    randomness: float = 0.0
    separation_pt: float = 0.0
    shift_pt: float = 0.0
    ramp: tuple[Colour, Colour] | None = None
    method: str = ""
    angle: float = 0.0


def load(text: str | bytes) -> JSON:
    """One ITEMS.CONTENT: JSON, then a NUL that is not JSON."""
    source = text.decode("utf-8") if isinstance(text, bytes) else text
    document, _end = json.JSONDecoder().raw_decode(source)
    if not isinstance(document, dict):
        raise ValueError("a CIM symbol is a JSON object")
    return document


def read_symbols(stylx: Path, names: Iterable[str]) -> dict[str, JSON]:
    """The named polygon symbols (CLASS 5), read without writing to the file."""
    wanted = list(names)
    uri = f"file:{stylx.resolve()}?mode=ro&immutable=1"
    marks = ",".join("?" * len(wanted))
    with sqlite3.connect(uri, uri=True) as db:
        rows = db.execute(
            f"SELECT NAME, CONTENT FROM ITEMS WHERE CLASS = 5 AND NAME IN ({marks})", wanted,
        ).fetchall()
    found = {str(name): load(content) for name, content in rows}
    missing = sorted(set(wanted) - found.keys())
    if missing:
        raise KeyError(f"not in {stylx.name}: {', '.join(missing)}")
    return found


def colour(value: JSON) -> Colour:
    """RGB, HSV or grey, with CIM's alpha in per cent as the last value."""
    kind, values = value["type"], [float(v) for v in value["values"]]
    if kind == "CIMRGBColor":
        rgb = values[:3]
    elif kind == "CIMHSVColor":
        h, s, v = values[:3]
        rgb = [c * 255 for c in colorsys.hsv_to_rgb(h / 360, s / 100, v / 100)]
    elif kind == "CIMGrayColor":
        rgb = [values[0]] * 3
    else:
        raise ValueError(f"unknown colour model {kind}")
    alpha = values[3] if len(values) > 3 else (values[1] if kind == "CIMGrayColor" else 100.0)
    return Colour("#" + "".join(f"{round(c):02x}" for c in rgb), alpha / 100)


def _effects(layer: JSON) -> dict[str, JSON]:
    return {e["type"].removeprefix("CIMGeometricEffect"): e for e in layer.get("effects") or []}


def _wave(effects: dict[str, JSON]) -> Wave | None:
    wave = effects.get("Wave")
    if wave is None:
        return None
    return Wave(float(wave["amplitude"]), float(wave["period"]), int(wave.get("seed", 0)))


def _picture(layer: JSON) -> bytes:
    url = str(layer["url"])
    if not url.startswith("data:image/png;base64,"):
        raise ValueError("a picture layer that is not an embedded PNG")
    # His base64 is broken into lines; anything else that is not base64 is refused.
    return base64.b64decode("".join(url.split(",", 1)[1].split()), validate=True)


def _stroke(layer: JSON, effects: dict[str, JSON]) -> Layer:
    picture = layer["type"] == "CIMPictureStroke"
    dashes = effects.get("Dashes", {}).get("dashTemplate", [])
    return Layer(
        "stroke",
        colour=colour(layer["tintColor"] if picture else layer["color"]),
        width_pt=float(layer["width"]),
        wave=_wave(effects),
        offset_pt=float(effects.get("Offset", {}).get("offset", 0.0)),
        dashes_pt=tuple(float(d) for d in dashes),
        image=_picture(layer) if picture else b"",
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
    )
    if layer["type"] == "CIMPictureMarker":
        return replace(placed, colour=colour(layer["tintColor"]), image=_picture(layer))
    if kind != "scatter":
        raise ValueError("a vector marker anywhere but strewn inside")
    ink, share = _grain(layer)
    return replace(placed, kind="grains", colour=ink, width_pt=share * placed.size_pt)


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
    ink = _stroke(line, _effects(line))
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
        size_pt=float(layer.get("gradientSize", 0.0)), wave=_wave(effects),
    )


def _layer(layer: JSON) -> Layer:
    kind, effects = layer["type"], _effects(layer)
    if kind in ("CIMSolidStroke", "CIMPictureStroke"):
        return _stroke(layer, effects)
    if kind == "CIMSolidFill":
        move = effects.get("Move", {})
        return Layer(
            "fill", colour=colour(layer["color"]), wave=_wave(effects),
            move_pt=(float(move.get("offsetX", 0.0)), float(move.get("offsetY", 0.0))),
        )
    if kind == "CIMPictureFill":
        return Layer("paper", colour=colour(layer["tintColor"]), image=_picture(layer),
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


__all__ = ["JSON", "Colour", "Layer", "Wave", "colour", "layers_of", "load", "read_symbols"]
