"""A tree is not a wall, and a bare tree is barely a tree."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from ninanatur.garden.canopies import (
    TRANSMISSION_BARE,
    TRANSMISSION_EVERGREEN,
    TRANSMISSION_IN_LEAF,
    deciduousness_of,
    transmission,
)
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.solar.shading import Obstacle

GIFT = {"source": "GIFT", "license": "CC-BY-4.0"}


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    c: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(c)
    for tid, name, leaves in ((1, "Picea abies", "evergreen"),
                              (2, "Quercus robur", "deciduous"),
                              (3, "Namenlos", None)):
        c.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (?, ?)", (tid, name))
        if leaves is not None:
            upsert_trait(c, tid, "deciduousness", value_text=leaves, **GIFT)
    c.commit()
    yield c


def test_a_conifer_lets_almost_nothing_through_all_year() -> None:
    for month in range(1, 13):
        assert transmission("evergreen", month) == TRANSMISSION_EVERGREEN


def test_a_broadleaf_in_leaf_lets_some_through() -> None:
    assert transmission("deciduous", 7) == TRANSMISSION_IN_LEAF


def test_a_bare_broadleaf_is_nearly_not_there() -> None:
    """The largest error the old model made. The light season starts on 1 March
    and a leafless oak was shading a garden exactly as hard as masonry, in the
    two months when somebody is deciding what to plant."""
    assert transmission("deciduous", 3) == TRANSMISSION_BARE
    assert transmission("deciduous", 4) == TRANSMISSION_BARE
    assert TRANSMISSION_BARE > TRANSMISSION_IN_LEAF * 3


def test_variable_is_treated_as_keeping_its_leaves() -> None:
    """A third answer GIFT actually gives, for 6 German woody species. A plant
    that keeps some of its leaves keeps some of its shade, and the other way
    round would make a garden brighter than it is."""
    assert transmission("variable", 3) == TRANSMISSION_EVERGREEN


def test_a_species_nobody_has_recorded_is_a_broadleaf() -> None:
    """53% of German woody species. Treating them as walls is what this feature
    exists to stop, so the fallback is the commonest kind of garden tree — and
    it still goes bare in March, which is the half that matters."""
    assert transmission(None, 7) == TRANSMISSION_IN_LEAF
    assert transmission(None, 3) == TRANSMISSION_BARE


def test_the_catalogue_answers_for_a_species(conn: sqlite3.Connection) -> None:
    assert deciduousness_of(conn, 1) == "evergreen"
    assert deciduousness_of(conn, 2) == "deciduous"
    assert deciduousness_of(conn, 3) is None


def test_an_obstacle_changes_with_the_season() -> None:
    oak = Obstacle(footprint=[(0, 0), (1, 0), (1, 1), (0, 1)], height=12.0,
                   transmission=TRANSMISSION_IN_LEAF,
                   bare_transmission=TRANSMISSION_BARE)

    assert oak.transmission_in(7) == TRANSMISSION_IN_LEAF
    assert oak.transmission_in(3) == TRANSMISSION_BARE


def test_a_wall_never_changes() -> None:
    """`bare_transmission` of None is what says "this is not a plant"."""
    wall = Obstacle(footprint=[(0, 0), (1, 0), (1, 1), (0, 1)], height=2.0)

    assert all(wall.transmission_in(m) == 0.0 for m in range(1, 13))


def test_a_spruce_takes_more_light_than_an_oak(conn: sqlite3.Connection) -> None:
    """End to end, through the light model. Two trees of the same size in the
    same place: the one that keeps its needles takes more of the year."""
    from ninanatur.garden.elements import insert_element
    from ninanatur.garden.lighting import recompute_light
    from ninanatur.garden.models import PLANTING_KIND
    from ninanatur.garden.plantings import add_planting, place_planting
    from ninanatur.garden.store import create_garden, load_garden

    def sun_under(taxon_id: int) -> float:
        c: sqlite3.Connection = connect(":memory:", same_thread=False)
        init_schema(c)
        for tid, leaves in ((1, "evergreen"), (2, "deciduous")):
            c.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (?, ?)",
                      (tid, f"Baum {tid}"))
            upsert_trait(c, tid, "deciduousness", value_text=leaves, **GIFT)
            upsert_trait(c, tid, "height_max_m", value_num=12.0, **GIFT)
            upsert_trait(c, tid, "growth_form", value_text="tree", **GIFT)
        c.commit()
        garden_id = create_garden(c, name="G", latitude=52.5, longitude=13.4)
        bed_id = insert_element(
            c, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
            name="Beet", points=[[0, 0], [8, 0], [8, 8], [0, 8]])
        c.commit()
        planting_id = add_planting(c, bed_id, taxon_id=taxon_id, quantity=1)
        place_planting(c, planting_id, 4.0, 4.0)
        recompute_light(c, garden_id)
        bed = load_garden(c, garden_id).beds[0]
        assert bed.sun_hours is not None
        return float(bed.sun_hours)

    spruce = sun_under(1)
    oak = sun_under(2)
    assert oak > spruce, f"oak {oak} h should beat spruce {spruce} h"


def test_a_tree_is_no_longer_a_wall(conn: sqlite3.Connection) -> None:
    """The change stated as a number. A crown that passes a fifth of the light
    is a different thing from masonry, and the bed underneath says so."""
    from ninanatur.solar.field import shadow_field
    from ninanatur.solar.position import Location

    where = Location(latitude=52.5, longitude=13.4)
    footprint = [(-2.0, 2.0), (2.0, 2.0), (2.0, 6.0), (-2.0, 6.0)]
    wall = Obstacle(footprint=footprint, height=12.0)
    crown = Obstacle(footprint=footprint, height=12.0,
                     transmission=TRANSMISSION_IN_LEAF,
                     bare_transmission=TRANSMISSION_BARE)

    # North of it. At 52.5 degrees the sun is in the south all year, so the
    # shadow falls north — a point to the south of an obstacle is never in it,
    # which is how the first version of this test measured nothing at all.
    under_wall = shadow_field(where, [wall]).sun_hours_at(0.0, 8.0)
    under_crown = shadow_field(where, [crown]).sun_hours_at(0.0, 8.0)

    assert under_crown > under_wall + 1.0, (
        f"crown {under_crown:.1f} h against wall {under_wall:.1f} h"
    )
