"""His symbols as data: CIM 2.3, as ArcGIS Pro keeps it in a .stylx (doc 97).

A .stylx is a SQLite database whose ITEMS table holds one JSON document per
symbol, each ending in a NUL. This reads them, and the colours, effects and
pictures inside them; `layers.py` turns a symbol into the layers the theme can
draw.
"""
from __future__ import annotations

import base64
import colorsys
import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

JSON = dict[str, Any]
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
    #: A ramp's method; how marks along a line vary in size.
    method: str = ""
    angle: float = 0.0
    #: Drawn on the outline scaled about its middle (his Scale effect).
    scale: float = 1.0
    #: Marks along a line: their sizes, as shares of `size_pt`, in the order used.
    sizes: tuple[float, ...] = ()
    #: How far along the line the first mark sits, and how far a mark may stray.
    start_pt: float = 0.0
    jitter_pt: float = 0.0


def load(text: str | bytes) -> JSON:
    """One ITEMS.CONTENT: JSON, then a NUL that is not JSON."""
    source = text.decode("utf-8") if isinstance(text, bytes) else text
    document, _end = json.JSONDecoder().raw_decode(source)
    if not isinstance(document, dict):
        raise ValueError("a CIM symbol is a JSON object")
    return document


def read_symbols(stylx: Path, names: Iterable[str], symbol_class: int = 5) -> dict[str, JSON]:
    """The named symbols of one class — 5 polygons, 4 lines — read without
    writing to the file."""
    wanted = list(names)
    uri = f"file:{stylx.resolve()}?mode=ro&immutable=1"
    marks = ",".join("?" * len(wanted))
    with sqlite3.connect(uri, uri=True) as db:
        rows = db.execute(
            f"SELECT NAME, CONTENT FROM ITEMS WHERE CLASS = ? AND NAME IN ({marks})",
            [symbol_class, *wanted],
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


def effects_of(layer: JSON) -> dict[str, JSON]:
    return {e["type"].removeprefix("CIMGeometricEffect"): e for e in layer.get("effects") or []}


def wave_of(effects: dict[str, JSON]) -> Wave | None:
    wave = effects.get("Wave")
    if wave is None:
        return None
    return Wave(float(wave["amplitude"]), float(wave["period"]), int(wave.get("seed", 0)))


def scale_of(effects: dict[str, JSON]) -> float:
    scale = effects.get("Scale")
    if scale is None:
        return 1.0
    if scale["xScaleFactor"] != scale["yScaleFactor"]:
        raise ValueError("a scale that stretches one way more than the other")
    return float(scale["xScaleFactor"])


def picture(layer: JSON) -> bytes:
    url = str(layer["url"])
    if not url.startswith("data:image/png;base64,"):
        raise ValueError("a picture layer that is not an embedded PNG")
    # His base64 is broken into lines; anything else that is not base64 is refused.
    return base64.b64decode("".join(url.split(",", 1)[1].split()), validate=True)


__all__ = ["JSON", "Colour", "Layer", "Wave", "colour", "effects_of", "load", "picture",
           "read_symbols", "scale_of", "wave_of"]
