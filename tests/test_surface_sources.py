"""The surface registry's rules, and the one thing it must agree with.

Same shape as `test_terrain_sources.py`: assert the rules rather than the
contents, so the tests survive a state being added and fail when one is added
carelessly.
"""
from __future__ import annotations

from ninanatur.geo.surface_sources import (
    NORMALISED,
    SURFACE,
    SURFACE_SOURCES,
    USABLE_CELL_M,
    by_state,
    measures_buildings,
)
from ninanatur.geo.terrain_sources import AXES_EN, AXES_XY
from ninanatur.geo.terrain_sources import TERRAIN_SOURCES

FORBIDDING = ("kostenpflichtig", "gebührenpflichtig", "non-commercial", "nc-")


def test_every_source_names_its_licence_and_its_credit() -> None:
    for source in SURFACE_SOURCES:
        assert source.licence.strip(), source.state
        assert source.attribution.strip(), source.state


def test_no_source_charges_for_this_use() -> None:
    """The gate that kept Saarland out of the terrain registry, applied again —
    a service being technically reachable is not the same as being usable."""
    for source in SURFACE_SOURCES:
        for word in FORBIDDING:
            assert word not in source.licence.lower(), f"{source.state}: {source.licence}"


def test_every_source_says_which_product_it_is() -> None:
    """`ndom` or `dom`, and the difference is not cosmetic: subtracting the
    terrain from an already-normalised model gives negative buildings, which
    looks like a bug in the shading rather than in the fetch."""
    for source in SURFACE_SOURCES:
        assert source.kind in (NORMALISED, SURFACE), source.state


def test_every_source_says_which_axes_and_which_zone() -> None:
    """Brandenburg's INSPIRE service wants x/y where the other INSPIRE services
    want E/N. Assuming otherwise cost a 404 before it was checked."""
    for source in SURFACE_SOURCES:
        assert source.axes in (AXES_XY, AXES_EN), source.state
        assert source.epsg in (25832, 25833), source.state


def test_a_surface_model_exists_wherever_terrain_does() -> None:
    """Not a coincidence to be relied on, but a property worth noticing if it
    ever stops holding: both come from the same laser scanning, and a state that
    publishes one usually publishes the other.

    If this fails, a state gained terrain without a surface model — which is
    fine, and means the building measurement has to say so for that state."""
    terrain = {s.state for s in TERRAIN_SOURCES}
    surface = {s.state for s in SURFACE_SOURCES}
    assert terrain == surface, f"only in terrain: {terrain - surface}"


def test_a_coarse_source_is_listed_and_refused() -> None:
    """Baden-Württemberg's 5 m coverage is real, open and correctly listed, and
    it still cannot say how tall one house is — a 5 m cell is wider than a small
    dwelling, so its value is a blend of roof and garden.

    Listing it and refusing it are different jobs, and doing them in one place
    would mean the registry quietly deciding what the caller may ask."""
    coarse = [s for s in SURFACE_SOURCES if not measures_buildings(s)]
    assert coarse, "the coarse entry was removed rather than refused"
    for source in coarse:
        assert source.cell_m > USABLE_CELL_M
        assert by_state(source.state) is not None, "it is still in the registry"


def test_the_finest_source_is_finer_than_the_terrain_beside_it() -> None:
    """NRW's nDOM is half a metre where its DGM1 is one. Worth asserting because
    a caller that assumes the two rasters share a cell size will be wrong there
    first."""
    nrw = by_state("Nordrhein-Westfalen")
    assert nrw is not None
    assert nrw.cell_m < 1.0


def test_a_state_with_no_surface_model_is_an_answer() -> None:
    assert by_state("Bayern") is None
    assert by_state("Freie Republik Erfundenien") is None


def test_lookup_does_not_care_about_case() -> None:
    assert by_state("berlin") is not None
    assert by_state("BERLIN") is not None
