"""Reading the model's shadow edge against a gardener's mark — doc 122.

Checked against what a hand can work out: a box's shadow ends height × cot h
from its sunny side, straight away from the sun. A mark there reads nothing;
a mark a metre beyond it reads the model a metre short, which a 9 m house at
a 30° sun amounts to 0.58 m of height; a mark beside the shadow reads a turn.

And against the review of 2026-09-28: only an edge on the ground is read, not
the thing's own sunlit walls (a mark in a lit courtyard read the courtyard's
wall); only an edge a top casts reads as a height (a crown's shadow also has a
near end, cast by where the crown starts); and a miss that runs straight away
from the thing is no turn of it.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import pytest

from ninanatur.garden.casting import casting
from ninanatur.garden.models import Element
from ninanatur.solar.position import Location, SunPosition, sun_position
from ninanatur.solar.shading import Obstacle
from ninanatur.solar.shadow_edge import read_edge

#: A box 2 m square and 9 m high, its middle at the origin.
BOX = Obstacle(footprint=[(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)], height=9.0)
#: The sun due south at 30°: the shadow runs north, 9·cot 30° = 15.59 m.
NOON = SunPosition(altitude=30.0, azimuth=180.0)
REACH = 9.0 / math.tan(math.radians(30.0))


def test_a_mark_where_the_model_ends_the_shadow_reads_nothing() -> None:
    reading = read_edge(BOX, NOON, 0.0, 1.0 + REACH)

    assert reading is not None
    assert reading.offset_m == pytest.approx(0.0, abs=1e-9)
    assert (reading.altitude, reading.azimuth, reading.edge) == (30.0, 180.0, "far")


def test_a_shadow_seen_longer_than_the_model_casts_reads_the_thing_as_too_low() -> None:
    """A metre beyond the model's edge: the model's shadow stops short, a
    metre towards the sun — as though the box stood tan 30° × 1 m lower."""
    reading = read_edge(BOX, NOON, 0.0, 2.0 + REACH)

    assert reading is not None
    assert reading.offset_m == pytest.approx(1.0)
    assert (reading.model_longer, reading.edge) == (False, "far")
    assert reading.along_m == pytest.approx(-1.0)
    assert reading.across_m == pytest.approx(0.0, abs=1e-9)
    assert reading.height_m == pytest.approx(-math.tan(math.radians(30.0)))
    assert reading.turned_deg is None
    assert reading.nearest == pytest.approx((0.0, 1.0 + REACH))


def test_a_shadow_seen_shorter_reads_the_thing_as_too_tall() -> None:
    """Half a metre short of the model's edge, inside its shadow (and nearer
    that edge than either side of a shadow 2 m wide)."""
    reading = read_edge(BOX, NOON, 0.0, 0.5 + REACH)

    assert reading is not None
    assert reading.model_longer is True, "the mark lies in the model's shadow"
    assert reading.along_m == pytest.approx(0.5)
    assert reading.height_m == pytest.approx(0.5 * math.tan(math.radians(30.0)))


def test_a_mark_beside_the_shadow_reads_a_turn_about_the_thing() -> None:
    """The model's shadow runs north; the gardener saw it end 2 m east of its
    eastern side. Its nearest edge is west of the mark — to the left, looking
    along the shadow — turned anticlockwise, seen from the thing. The same
    off the origin: the angle is the thing's, not the plan's."""
    for cx, cy in ((0.0, 0.0), (10.0, -4.0)):
        box = Obstacle(footprint=[(cx - 1, cy - 1), (cx + 1, cy - 1), (cx + 1, cy + 1),
                                  (cx - 1, cy + 1)], height=9.0)
        reading = read_edge(box, NOON, cx + 3.0, cy + 12.0)

        assert reading is not None
        assert reading.offset_m == pytest.approx(2.0)
        assert reading.edge == "side"
        assert reading.across_m == pytest.approx(2.0)
        assert reading.height_m is None
        expected = math.degrees(math.atan2(12.0, 1.0) - math.atan2(12.0, 3.0))
        assert reading.turned_deg == pytest.approx(expected)


def test_at_a_corner_the_way_the_miss_runs_says_which_edge_it_is() -> None:
    """Nearest a corner of the shadow, two edges are equally near. A miss
    that runs mostly along the sun is about the far edge, and reads a height;
    one mostly across it is about the side (review of stage 3: ring order
    decided, and a miss along the sun read "seitlich")."""
    block = Obstacle(footprint=[(-5.0, -4.0), (5.0, -4.0), (5.0, 4.0), (-5.0, 4.0)],
                     height=9.0)
    sun = SunPosition(altitude=40.0, azimuth=180.0)
    corner_y = 4.0 + 9.0 / math.tan(math.radians(40.0))
    along = read_edge(block, sun, 5.8, corner_y + 1.8)
    across = read_edge(block, sun, 7.0, corner_y + 0.5)
    assert along is not None and across is not None
    assert (along.edge, along.height_m is not None) == ("far", True)
    assert (across.edge, across.height_m) == ("side", None)


def test_a_miss_straight_towards_the_thing_is_no_turn() -> None:
    """An evening sun from the west: the shadow runs east. A mark 4 m north of
    the box, beside its shadow, reads a miss that points at the box — which a
    turn of the plan cannot make (review, 2026-09-28: it read 0°)."""
    reading = read_edge(BOX, SunPosition(altitude=30.0, azimuth=270.0), 0.0, 5.0)

    assert reading is not None
    assert reading.offset_m == pytest.approx(4.0)
    assert reading.turned_deg is None and reading.height_m is None


def test_a_lit_courtyard_is_read_against_the_shadow_in_it_not_its_wall() -> None:
    """A house round a courtyard, 3 m high, a 30° sun from the south. Its
    southern wing's shadow reaches 3·cot 30° = 5.2 m into the courtyard, to
    y = 0.196; the mark at y = 3 lies in the lit part, and its nearest edge
    on the ground is that shadow's end — not the foot of the courtyard's lit
    northern wall at y = 5, which the drawn shadow holds as well."""
    house = Obstacle(footprint=[(-10, -10), (10, -10), (10, -2), (5, -2), (5, -5), (-5, -5),
                                (-5, 5), (5, 5), (5, 2), (10, 2), (10, 10), (-10, 10)],
                     height=3.0)
    reading = read_edge(house, NOON, 0.0, 3.0)

    assert reading is not None
    assert reading.nearest[1] == pytest.approx(-5.0 + 3.0 / math.tan(math.radians(30.0)))
    assert (reading.model_longer, reading.edge) == (False, "far")
    assert reading.height_m is not None and reading.height_m < 0, "the model's house too low"


def test_where_a_crowns_shadow_begins_is_no_height() -> None:
    """A tree of 12 m, its crown 8 m across from 4 m: at a 30° sun its shadow
    begins a way north of the trunk, cast by where the crown starts. A mark on
    either side of that near end reads the edge as near, and says nothing
    about a height the top would have cast."""
    tree = casting(Element(element_id=2, kind="tree", shape="circle", x=0.0, y=0.0,
                           width=8.0, height=12.0))
    begins = read_edge(tree, NOON, 0.0, 30.0)
    assert begins is not None
    near_end = min(y for ring in begins.rings for _x, y in ring)
    for y in (near_end - 0.5, near_end + 0.5):
        reading = read_edge(tree, NOON, 0.0, y)
        assert reading is not None
        assert (reading.edge, reading.height_m) == ("near", None), y


def test_the_edge_is_the_one_the_model_casts_a_roof_and_a_crown_with() -> None:
    """Read through the caster the light model uses (`garden.casting`): a
    gabled house's shadow ends where its ridge's does, not where a block's
    would; a tree's where its crown's ellipse does, not its cylinder's."""
    house = casting(Element(element_id=1, kind="house", shape="polygon", x=0.0, y=0.0,
                            points=[[-6, -4], [6, -4], [6, 4], [-6, 4]], height=9.0,
                            roof="gable", eaves_m=5.0))
    ridge = read_edge(house, NOON, 0.0, REACH + 1.0)
    assert ridge is not None
    # The ridge runs east–west along the long side, at y = 0: its shadow ends
    # 9·cot 30° north of it.
    assert ridge.nearest[1] == pytest.approx(REACH, abs=0.05)

    tree = casting(Element(element_id=2, kind="tree", shape="circle", x=0.0, y=0.0,
                           width=8.0, height=12.0))
    crown = read_edge(tree, NOON, 0.0, 30.0)
    assert crown is not None
    # The crown, 4 m to 12 m, a sphere round (0, 0, 8): its shadow's far end
    # lies 8·cot 30° + 4/sin 30° north.
    far = 8.0 / math.tan(math.radians(30.0)) + 4.0 / math.sin(math.radians(30.0))
    assert crown.nearest[1] == pytest.approx(far, abs=0.05)
    assert crown.edge == "far"


def test_the_shadow_ends_where_nrels_sun_and_a_hand_put_it() -> None:
    """The one synthetic case doc 122 compares against what shares nothing
    with the model: NREL's SPA for the sun (the reference table pvlib made
    for doc 115) and trigonometry for the shadow. A block 10 × 8 m and 9 m
    high near Osnabrück, 13 August 2026, 11:38:25 UTC: its northern corners'
    shadows lie 9·cot h away from them, straight away from SPA's sun."""
    reference = json.loads((Path(__file__).parent / "fixtures" / "sun_reference.json")
                           .read_text(encoding="utf-8"))
    [(lat, lon, utc, elevation, azimuth)] = [
        row for row in reference["rows"] if row[2] == "2026-08-13T11:38:25Z"]
    reach = 9.0 / math.tan(math.radians(elevation))
    away = math.radians(azimuth)
    shift = (-math.sin(away) * reach, -math.cos(away) * reach)
    by_hand = [(-5.0 + shift[0], 4.0 + shift[1]), (5.0 + shift[0], 4.0 + shift[1])]

    block = Obstacle(footprint=[(-5.0, -4.0), (5.0, -4.0), (5.0, 4.0), (-5.0, 4.0)],
                     height=9.0)
    sun = sun_position(Location(lat, lon), datetime.fromisoformat(utc.replace("Z", "+00:00")))
    for corner in by_hand:
        reading = read_edge(block, sun, *corner)
        assert reading is not None
        assert reading.offset_m < 0.01, (corner, reading.nearest)
        drawn = min(math.hypot(x - corner[0], y - corner[1])
                    for ring in reading.rings for x, y in ring)
        assert drawn < 0.01, "a corner of the drawn shadow is there"
