"""Soil as gardeners describe it, mapped to the axes the data uses."""
import pytest

from ninanatur.garden.soil import (
    MOISTURE_TO_M,
    SOIL_TO_RN,
    MoistureError,
    SoilTypeError,
    site_axes_from_soil,
)


def test_the_user_never_supplies_an_ellenberg_value() -> None:
    axes = site_axes_from_soil(soil_type="loam", moisture="fresh")
    assert set(axes) == {"ellenberg_m", "ellenberg_n", "ellenberg_r"}


def test_sand_is_poorer_and_more_acid_than_clay() -> None:
    sand = site_axes_from_soil("sand", "fresh")
    clay = site_axes_from_soil("clay", "fresh")
    assert sand["ellenberg_n"] < clay["ellenberg_n"]
    assert sand["ellenberg_r"] < clay["ellenberg_r"]


def test_moisture_is_ordered_from_dry_to_wet() -> None:
    levels = ("dry", "fresh", "moist", "wet")
    values = [site_axes_from_soil("loam", m)["ellenberg_m"] for m in levels]
    assert values == sorted(values)


def test_humus_is_the_most_nutrient_rich() -> None:
    richest = max(SOIL_TO_RN, key=lambda k: SOIL_TO_RN[k][1])
    assert richest == "humus"


def test_an_unknown_soil_type_is_rejected_not_silently_defaulted() -> None:
    """A typo defaulting to loam would produce confident, wrong suggestions."""
    with pytest.raises(SoilTypeError):
        site_axes_from_soil("concrete", "fresh")


def test_an_unknown_moisture_is_rejected() -> None:
    with pytest.raises(MoistureError):
        site_axes_from_soil("loam", "damp-ish")


def test_every_documented_option_is_actually_accepted() -> None:
    for soil in SOIL_TO_RN:
        for moisture in MOISTURE_TO_M:
            assert site_axes_from_soil(soil, moisture)
