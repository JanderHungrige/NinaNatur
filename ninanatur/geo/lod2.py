"""What the survey says a roof looks like.

A surface model says how tall a building is. Only the official 3D building model
says what shape its roof has — and Wave 16 currently asks a person to answer
that, per building, for buildings that are not theirs and that they may never
have seen from the side.

Nordrhein-Westfalen publishes LoD2 as CityGML in **addressable 1 km² tiles**:
the name is computable from the UTM coordinates, so there is no search step. A
Cologne tile holds 2,189 buildings and every one of them carries `measuredHeight`
and `roofType`.

**Tile in, table out.** The tile is tens of megabytes and is not a thing to keep;
what is kept is a few hundred bytes per building. Streamed rather than read into
memory, because a 38 MB document parsed into a tree is 38 MB of tree.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from xml.etree import ElementTree

from ninanatur.garden.roofs import Roof

#: AdV's Dachform key onto the shapes the shading model has a ratio for.
#:
#: `Mischform` and `Sonstiges` are surveyed answers, not absences, and they get
#: their own members — a fifth of the buildings in a Cologne tile are Mischform,
#: and calling that "unknown" would throw away the one thing that separates a
#: measurement from nobody having looked.
ADV_ROOFS: dict[str, Roof] = {
    "1000": Roof.FLAT,
    "2100": Roof.PENT,
    "2200": Roof.PENT,       # versetztes Pultdach
    "3100": Roof.GABLE,
    "3200": Roof.HIP,
    "3300": Roof.HIP,        # Krüppelwalmdach
    "3400": Roof.GABLE,      # Mansarddach: a gable with a kink in it
    "3500": Roof.HIP,        # Zeltdach, a pyramid
    "3600": Roof.OTHER,      # Kegeldach
    "3700": Roof.OTHER,      # Kuppeldach
    "3800": Roof.OTHER,      # Sheddach
    "3900": Roof.OTHER,      # Bogendach
    "4000": Roof.OTHER,      # Turmdach
    "5000": Roof.MIX,        # Mischform
    "9999": Roof.OTHER,      # Sonstiges
}

_NS = {"bldg": "http://www.opengis.net/citygml/building/1.0",
       "gml": "http://www.opengis.net/gml"}
_POS = re.compile(r"[-\d.eE+]+")


@dataclass(frozen=True)
class Lod2Building:
    """One surveyed building: what shape, how tall, and roughly where."""

    building_id: str
    roof: Roof
    #: Ridge height above the ground it stands on, in metres.
    height_m: float
    #: Its ground plan in the tile's own UTM coordinates. Enough to match
    #: against an OSM footprint; not enough to draw with.
    outline: list[tuple[float, float]]
    #: Where the walls stop and the roof starts, above the same ground. None
    #: where the geometry did not say — then the shading model falls back to its
    #: three-quarters assumption, as it did for every building until now.
    eaves_m: float | None = None

    @property
    def centre(self) -> tuple[float, float]:
        n = len(self.outline) or 1
        return (
            sum(p[0] for p in self.outline) / n,
            sum(p[1] for p in self.outline) / n,
        )


def tile_name(east: float, north: float) -> str:
    """The NRW tile covering a point, from its UTM32 coordinates.

    `LoD2_32_354_5643_1_NW.gml` is zone 32, easting 354 km, northing 5643 km,
    one kilometre square. Computable rather than searchable, which is the
    difference between one request and an index lookup.
    """
    return f"LoD2_32_{int(east) // 1000}_{int(north) // 1000}_1_NW.gml"


def buildings_from(document: bytes) -> list[Lod2Building]:
    """Every building in a CityGML tile, distilled.

    Streamed with `iterparse` and cleared as it goes: a 38 MB document read into
    a tree is 38 MB of tree, and the useful part of it is a few hundred bytes
    per building.

    **Parts count as buildings, and forgetting them loses a third of the tile.**
    CityGML lets a building consist of `BuildingPart`s — a wing with its own roof
    and its own height — and then the building itself carries neither. In the
    Cologne tile 385 of 1,332 buildings are like that, made of 1,242 parts
    between them, and a parser that reads only top-level buildings returns 947
    where the tile holds 2,189 roofs.

    Emitting each part separately is also the better answer for shading: a long
    wing with a low roof beside a tall gabled one is two prisms, and treating it
    as one would shade with whichever height happened to win.

    An element missing a height or a roof type is skipped rather than defaulted —
    a building made of parts is exactly that case, and its parts are picked up on
    their own.
    """
    found: list[Lod2Building] = []
    for _event, element in ElementTree.iterparse(BytesIO(document), events=("end",)):
        if not (element.tag.endswith("}Building") or element.tag.endswith("}BuildingPart")):
            continue
        building = _one(element)
        if building is not None:
            found.append(building)
            # Only cleared once it has been read. A part ends before its parent,
            # and clearing it early would leave the parent no geometry to find —
            # which does not arise today, because a parent with parts carries no
            # roof of its own and is skipped, but would the moment one did.
            element.clear()
    return found


def _one(element: ElementTree.Element) -> Lod2Building | None:
    roof_code = element.findtext("bldg:roofType", namespaces=_NS)
    height = element.findtext("bldg:measuredHeight", namespaces=_NS)
    if roof_code is None or height is None:
        return None
    roof = ADV_ROOFS.get(roof_code.strip())
    if roof is None:
        # An AdV code nobody here has a ratio for. `other` rather than a guess:
        # the surveyor did look, and the honest reading of an unmapped code is
        # "a shape this model does not model".
        roof = Roof.OTHER
    outline, ground_z, roof_low_z = _surfaces(element)
    if not outline:
        return None
    eaves = None
    if roof_low_z is not None and ground_z is not None:
        gap = roof_low_z - ground_z
        # A flat roof's surface sits at the top, so its "eaves" would be the
        # whole building and mean nothing. Anything at or above the ridge is
        # discarded for the same reason.
        if 0.0 < gap < float(height):
            eaves = round(gap, 2)
    return Lod2Building(
        building_id=element.get(f"{{{_NS['gml']}}}id", ""),
        roof=roof,
        height_m=float(height),
        outline=outline,
        eaves_m=eaves,
    )


def _surfaces(
    element: ElementTree.Element,
) -> tuple[list[tuple[float, float]], float | None, float | None]:
    """The ground plan, the height it sits at, and where the roof begins.

    LoD2 labels its faces: every building carries exactly one `GroundSurface`
    — 2,189 of them in a tile with 2,189 roofs — so the footprint is read rather
    than inferred. An earlier version took "the ring whose points sit lowest",
    which is the same answer for a building on level ground and quietly a wall
    for one on a slope.

    The lowest point of the `RoofSurface`s is the eaves. It is only meaningful
    for a pitched roof; on a flat one the roof surface *is* the top, and the
    caller discards a gap that reaches the ridge.
    """
    ground: list[tuple[float, float]] = []
    ground_z: float | None = None
    roof_low: float | None = None

    for face in element.iter():
        if face.tag.endswith("}GroundSurface"):
            rings = _rings(face)
            if rings and not ground:
                ground = [(x, y) for x, y, _z in rings]
                ground_z = sum(z for _x, _y, z in rings) / len(rings)
        elif face.tag.endswith("}RoofSurface"):
            rings = _rings(face)
            if rings:
                low = min(z for _x, _y, z in rings)
                roof_low = low if roof_low is None else min(roof_low, low)
    return ground, ground_z, roof_low


def _rings(face: ElementTree.Element) -> list[tuple[float, float, float]]:
    """Every three-dimensional point under one labelled face."""
    points: list[tuple[float, float, float]] = []
    for pos in face.iter():
        if not pos.tag.endswith("posList") or not pos.text:
            continue
        numbers = [float(v) for v in _POS.findall(pos.text)]
        if len(numbers) < 9 or len(numbers) % 3:
            continue
        points.extend(
            (numbers[i], numbers[i + 1], numbers[i + 2])
            for i in range(0, len(numbers), 3)
        )
    return points


__all__ = ["ADV_ROOFS", "Lod2Building", "buildings_from", "tile_name"]
