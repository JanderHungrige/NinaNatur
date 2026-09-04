"""What you plant changes the site.

A bed is a marked area, and a tree standing in it is not a different kind of
bed — it is a thing that casts a shadow. The shading machinery already models
obstacles as vertical cylinders, which is exactly the shape of a tree; it simply
was never told about the ones the user plants.
"""
import sqlite3
from collections.abc import Iterator

import pytest

from ninanatur.garden.lighting import recompute_light
from ninanatur.garden.models import BedInput
from ninanatur.garden.plantings import add_planting, place_planting, remove_planting
from ninanatur.garden.store import add_bed, create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait

GIFT = {"source": "GIFT", "license": "CC-BY-4.0"}
SOUTH = [[0.0, -6.0], [4.0, -6.0], [4.0, -2.0], [0.0, -2.0]]
HERE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    c = connect(":memory:")
    init_schema(c)
    for tid, name, height, form in (
        (1, "Quercus robur", 24.0, "tree"),
        (2, "Campanula rotundifolia", 0.4, "forb"),
        (3, "Namenlos", None, "shrub"),
        (4, "Corylus avellana", 3.0, "shrub"),
    ):
        c.execute(
            "INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
            (tid, name),
        )
        if height is not None:
            upsert_trait(c, tid, "height_max_m", value_num=height, **GIFT)
        upsert_trait(c, tid, "growth_form", value_text=form, **GIFT)
    c.commit()
    yield c


def _sunny_garden(c: sqlite3.Connection) -> tuple[int, int]:
    garden_id = create_garden(c, name="G", latitude=52.5, longitude=13.4)
    bed_id = add_bed(
        c, garden_id, BedInput(name="Beet", polygon=HERE, soil_type="loam", moisture="fresh")
    )
    recompute_light(c, garden_id)
    return garden_id, bed_id


def _sun_hours(c: sqlite3.Connection, garden_id: int, bed_id: int) -> float:
    bed = next(b for b in load_garden(c, garden_id).beds if b.bed_id == bed_id)
    assert bed.sun_hours is not None
    return float(bed.sun_hours)


def _light(c: sqlite3.Connection, garden_id: int, bed_id: int) -> float:
    bed = next(b for b in load_garden(c, garden_id).beds if b.bed_id == bed_id)
    assert bed.ellenberg_l is not None
    return float(bed.ellenberg_l)


def test_a_full_grown_oak_darkens_the_bed_it_stands_in(conn: sqlite3.Connection) -> None:
    """Reversed in Wave 16, and this one is not the interesting half.

    A 24 m oak has a crown 16 m across. Standing in a 4 x 4 m bed it covers the
    whole of it and a good deal besides, so the bed going dark is the right
    answer and not an artifact.

    The bed used to be excluded from its own plantings, for a reason that was
    sound at the time: a planting had no position, so it sat at the bed's
    centroid — which was also the single point the light was sampled at. Every
    plant therefore stood exactly on the sample point, and even a 2 m shrub took
    the bed to zero. Wave 15 gave clusters coordinates and Wave 16 samples a
    grid, so both halves of that artifact are gone.
    """
    garden_id, bed_id = _sunny_garden(conn)
    before = _light(conn, garden_id, bed_id)

    add_planting(conn, bed_id, taxon_id=1, quantity=1)
    recompute_light(conn, garden_id)

    assert _light(conn, garden_id, bed_id) < before


def test_a_hazel_in_the_corner_costs_the_corner(conn: sqlite3.Connection) -> None:
    """The half that shows what the grid bought.

    A 3 m hazel has a 3 m crown. In a 16 m² bed it takes a share of the light
    and not the lot — which the old model could not express at all, because it
    sampled one point and the plant stood on it.
    """
    garden_id, bed_id = _sunny_garden(conn)
    before = _sun_hours(conn, garden_id, bed_id)

    planting_id = add_planting(conn, bed_id, taxon_id=4, quantity=1)
    place_planting(conn, planting_id, 0.8, 0.8)
    recompute_light(conn, garden_id)
    after = _sun_hours(conn, garden_id, bed_id)

    assert after < before, "it does cast a shadow onto its own bed"
    assert after > before * 0.5, "and it is a corner, not the whole bed"


def test_planting_a_harebell_changes_nothing(conn: sqlite3.Connection) -> None:
    # A 40 cm perennial's shadow falls inside its own footprint.
    garden_id, bed_id = _sunny_garden(conn)
    before = _light(conn, garden_id, bed_id)

    add_planting(conn, bed_id, taxon_id=2, quantity=1)
    recompute_light(conn, garden_id)

    assert _light(conn, garden_id, bed_id) == before


def test_a_tree_shades_the_bed_to_its_north(conn: sqlite3.Connection) -> None:
    """The point of modelling it at all: the shadow leaves the bed it stands in."""
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    south = add_bed(
        conn, garden_id, BedInput(name="Süd", polygon=SOUTH, soil_type="loam", moisture="fresh")
    )
    north = add_bed(
        conn, garden_id, BedInput(name="Nord", polygon=HERE, soil_type="loam", moisture="fresh")
    )
    recompute_light(conn, garden_id)
    before = _light(conn, garden_id, north)

    add_planting(conn, south, taxon_id=1, quantity=1)
    recompute_light(conn, garden_id)

    assert _light(conn, garden_id, north) < before


def test_a_species_with_no_recorded_height_casts_no_shadow(conn: sqlite3.Connection) -> None:
    """Absent data is not a property of the plant, and it is not a licence to
    invent a 5 m shrub either."""
    garden_id, bed_id = _sunny_garden(conn)
    before = _light(conn, garden_id, bed_id)

    add_planting(conn, bed_id, taxon_id=3, quantity=1)
    recompute_light(conn, garden_id)

    assert _light(conn, garden_id, bed_id) == before


def test_planting_a_tree_recomputes_the_light_without_being_asked(
    conn: sqlite3.Connection,
) -> None:
    """The integration gap the unit tests could not see.

    Every other test here calls `recompute_light` itself, so each one passed
    while the running app left the bed at 12.6 h and Ellenberg 8 with a 24 m oak
    standing in it. The invariant belongs to the store for the same reason the
    light computation itself does: it has to hold whatever the entry point.
    """
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    south = add_bed(
        conn, garden_id, BedInput(name="Süd", polygon=SOUTH, soil_type="loam", moisture="fresh")
    )
    north = add_bed(
        conn, garden_id, BedInput(name="Nord", polygon=HERE, soil_type="loam", moisture="fresh")
    )
    recompute_light(conn, garden_id)
    before = _light(conn, garden_id, north)

    add_planting(conn, south, taxon_id=1, quantity=1)

    assert _light(conn, garden_id, north) < before


def test_planting_a_perennial_does_not_trigger_a_recompute(
    conn: sqlite3.Connection,
) -> None:
    # Recomputing the whole garden on every perennial would be work with no
    # possible effect: nothing under 1.5 m casts a shadow anyone can use.
    garden_id, bed_id = _sunny_garden(conn)
    before = _light(conn, garden_id, bed_id)
    add_planting(conn, bed_id, taxon_id=2, quantity=1)
    assert _light(conn, garden_id, bed_id) == before


def test_removing_the_tree_gives_the_light_back(conn: sqlite3.Connection) -> None:
    """The other direction, which is easy to forget: a bed left permanently dark
    by a tree that is no longer there would be worse than never shading at all."""
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    south = add_bed(
        conn, garden_id, BedInput(name="Süd", polygon=SOUTH, soil_type="loam", moisture="fresh")
    )
    north = add_bed(
        conn, garden_id, BedInput(name="Nord", polygon=HERE, soil_type="loam", moisture="fresh")
    )
    recompute_light(conn, garden_id)
    before = _light(conn, garden_id, north)
    planting_id = add_planting(conn, south, taxon_id=1, quantity=1)
    assert _light(conn, garden_id, north) < before

    remove_planting(conn, planting_id)

    assert _light(conn, garden_id, north) == before
