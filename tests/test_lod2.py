"""Reading the official building model, and the third of it that is easy to lose.

CityGML is built here rather than fetched. The document is small and the point
is the shapes it can take — a building made of parts, a labelled ground surface,
a roof plane that is not the footprint — none of which a fixture from one tile
would exercise on purpose.
"""
from __future__ import annotations

import pytest

from ninanatur.garden.roofs import Roof
from ninanatur.geo.lod2 import ADV_ROOFS, buildings_from, tile_name

HEAD = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<core:CityModel xmlns:core="http://www.opengis.net/citygml/1.0" '
    'xmlns:bldg="http://www.opengis.net/citygml/building/1.0" '
    'xmlns:gml="http://www.opengis.net/gml">'
)
TAIL = "</core:CityModel>"


def _surface(kind: str, points: list[tuple[float, float, float]]) -> str:
    flat = " ".join(f"{x} {y} {z}" for x, y, z in points)
    return (
        f"<bldg:boundedBy><bldg:{kind}><bldg:lod2MultiSurface><gml:MultiSurface>"
        f"<gml:surfaceMember><gml:Polygon><gml:exterior><gml:LinearRing>"
        f"<gml:posList>{flat}</gml:posList>"
        "</gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember>"
        "</gml:MultiSurface></bldg:lod2MultiSurface></bldg:"
        f"{kind}></bldg:boundedBy>"
    )


SQUARE = [(0.0, 0.0, 100.0), (10.0, 0.0, 100.0), (10.0, 10.0, 100.0),
          (0.0, 10.0, 100.0), (0.0, 0.0, 100.0)]
#: A roof plane, offset from the footprint and six metres up — the shape that
#: made "take the lowest ring" wrong for a building on a slope.
ROOF = [(0.0, 0.0, 106.0), (10.0, 0.0, 106.0), (5.0, 5.0, 110.0), (0.0, 0.0, 106.0)]


def _building(gml_id: str, roof: str, height: str, inner: str = "") -> str:
    return (
        f'<bldg:Building gml:id="{gml_id}">'
        f"<bldg:roofType>{roof}</bldg:roofType>"
        f'<bldg:measuredHeight uom="urn:adv:uom:m">{height}</bldg:measuredHeight>'
        + _surface("GroundSurface", SQUARE) + _surface("RoofSurface", ROOF)
        + inner + "</bldg:Building>"
    )


def test_one_building_comes_back_whole() -> None:
    [b] = buildings_from((HEAD + _building("DE_1", "3100", "10.0") + TAIL).encode())

    assert b.building_id == "DE_1"
    assert b.roof is Roof.GABLE
    assert b.height_m == pytest.approx(10.0)
    assert len(b.outline) == 5


def test_a_building_made_of_parts_yields_the_parts_and_not_itself() -> None:
    """The third of the tile that is easy to lose. CityGML lets a building
    consist of wings, each with its own roof and height, and then the building
    carries neither — 385 of 1,332 in the Cologne tile are like that, and a
    parser reading only top-level buildings returned 947 where the tile holds
    2,189 roofs."""
    parts = (
        "<bldg:consistsOfBuildingPart>"
        + _building("DE_A", "1000", "12.0").replace("bldg:Building", "bldg:BuildingPart")
        + "</bldg:consistsOfBuildingPart>"
        "<bldg:consistsOfBuildingPart>"
        + _building("DE_B", "3100", "8.0").replace("bldg:Building", "bldg:BuildingPart")
        + "</bldg:consistsOfBuildingPart>"
    )
    document = (
        HEAD + f'<bldg:Building gml:id="DE_WHOLE">{parts}</bldg:Building>' + TAIL
    )

    found = buildings_from(document.encode())

    assert {b.building_id for b in found} == {"DE_A", "DE_B"}
    assert {b.height_m for b in found} == {12.0, 8.0}


def test_a_wing_keeps_its_own_roof_and_its_own_height() -> None:
    """Which is why parts are emitted separately rather than merged: a long low
    wing beside a tall gabled one is two prisms, and treating it as one would
    shade with whichever height happened to win."""
    parts = (
        "<bldg:consistsOfBuildingPart>"
        + _building("DE_LOW", "1000", "4.0").replace("bldg:Building", "bldg:BuildingPart")
        + "</bldg:consistsOfBuildingPart>"
    )
    document = HEAD + f'<bldg:Building gml:id="W">{parts}</bldg:Building>' + TAIL

    [wing] = buildings_from(document.encode())

    assert wing.roof is Roof.FLAT
    assert wing.height_m == pytest.approx(4.0)


def test_the_footprint_is_the_labelled_ground_and_not_a_roof_plane() -> None:
    """An earlier version took "the ring whose points sit lowest", which is the
    same answer on level ground and quietly a wall for a building on a slope."""
    [b] = buildings_from((HEAD + _building("DE_2", "3100", "10.0") + TAIL).encode())

    assert (5.0, 5.0) not in b.outline, "that vertex is the ridge"
    assert (10.0, 10.0) in b.outline


def test_the_eaves_come_out_of_the_same_parse() -> None:
    """Roof surfaces start six metres above a ground surface at 100, so the
    walls are six metres tall. Measured, where until now this was three quarters
    of the height by assumption."""
    [b] = buildings_from((HEAD + _building("DE_3", "3100", "10.0") + TAIL).encode())

    assert b.eaves_m == pytest.approx(6.0)


def test_an_eaves_at_the_ridge_is_no_eaves_at_all() -> None:
    """A flat roof's surface *is* its top, so the gap would be the whole
    building and mean nothing."""
    flat_roof = [(0.0, 0.0, 110.0), (10.0, 0.0, 110.0), (10.0, 10.0, 110.0),
                 (0.0, 0.0, 110.0)]
    document = (
        HEAD
        + '<bldg:Building gml:id="DE_4"><bldg:roofType>1000</bldg:roofType>'
        '<bldg:measuredHeight>10.0</bldg:measuredHeight>'
        + _surface("GroundSurface", SQUARE) + _surface("RoofSurface", flat_roof)
        + "</bldg:Building>" + TAIL
    )

    [b] = buildings_from(document.encode())

    assert b.eaves_m is None


def test_something_with_no_roof_type_is_skipped_rather_than_defaulted() -> None:
    """Every one of 2,189 in the tile carried both a height and a roof, so a
    missing one means the product changed — and a default would hide that."""
    document = (
        HEAD + '<bldg:Building gml:id="DE_5">'
        "<bldg:measuredHeight>9.0</bldg:measuredHeight>"
        + _surface("GroundSurface", SQUARE) + "</bldg:Building>" + TAIL
    )

    assert buildings_from(document.encode()) == []


def test_mischform_and_sonstiges_are_answers_not_absences() -> None:
    """A surveyor looked. Collapsing them into `unknown` would throw away the
    one thing that separates a measurement from nobody having looked."""
    assert ADV_ROOFS["5000"] is Roof.MIX
    assert ADV_ROOFS["9999"] is Roof.OTHER
    assert Roof.UNKNOWN not in ADV_ROOFS.values()


def test_an_unmapped_adv_code_becomes_other_rather_than_unknown() -> None:
    """Same reasoning: the code was recorded, this model simply has no ratio for
    that shape."""
    [b] = buildings_from((HEAD + _building("DE_6", "4711", "10.0") + TAIL).encode())
    assert b.roof is Roof.OTHER


def test_the_tile_name_is_computed_not_searched() -> None:
    """One request instead of an index lookup."""
    assert tile_name(354169.0, 5643535.0) == "LoD2_32_354_5643_1_NW.gml"
