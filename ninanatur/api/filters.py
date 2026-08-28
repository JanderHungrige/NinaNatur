"""What a filter decides about a species, and what it admits it dropped.

Split from `search.py` so the ranking module holds ranking. The rules here are
the ones the catalogue's coverage forces: height is recorded for 44% of German
species and flower colour for 6.6%, so "does not match" and "we never recorded
it" cannot be the same answer.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ninanatur.api.candidates import PlantRow
from ninanatur.bloom.timeline import flowering_months

# Growth forms that are not bed plants. A bed is a few square metres; a hemlock
# fits its light and moisture perfectly and is still a useless suggestion.
WOODY_FORMS: frozenset[str] = frozenset({"tree", "shrub"})

# Above this a plant is not going in a flower bed whatever its recorded form.
# Used as a second signal because growth form is missing for part of the
# catalogue — 25 German candidates are this tall with no form recorded.
WOODY_HEIGHT_M = 3.0

# Species whose German origin is recorded as introduced. Excluded by default,
# because the product promises native plants — 1,071 of the 3,087 suggestible
# species are introduced, and every one of them was being offered as heimisch.
#
# Unknown is NOT excluded: that is a gap in the data, not a property of the
# plant, the same rule that keeps flower colour a soft filter.
INTRODUCED = "introduced"

# The closed set of growth forms the catalogue actually records. A closed set
# rather than a free string: the value never reaches SQL, but an unbounded
# parameter that silently matches nothing is its own kind of lie.
GROWTH_FORMS: frozenset[str] = frozenset(
    {"forb", "herb", "graminoid", "shrub", "subshrub", "tree"}
)


class Verdict(Enum):
    """What one filter decided about one species.

    UNKNOWN is a third answer on purpose. Height is recorded for 44% of the
    catalogue and colour for 6.6%; collapsing "does not match" and "we never
    recorded it" into one boolean is how a filter silently drops 4,987 species
    and reports nothing. Coverage tracks how well-studied a plant is, so a
    coverage-blind filter quietly favours the familiar.
    """

    MATCH = "match"
    UNKNOWN = "unknown"
    MISMATCH = "mismatch"


@dataclass
class FilterCounts:
    """How one active filter divided the candidate set."""

    matched: int = 0
    unknown: int = 0
    excluded: int = 0

    def record(self, verdict: Verdict, *, excludes: bool) -> None:
        """Count one species.

        A MISMATCH only lands in `excluded` for a filter that actually excludes.
        Colour ranks instead, so its `excluded` stays 0 and its mismatches are
        simply ordered down — the counts must not claim a removal that never
        happened.
        """
        if verdict is Verdict.MATCH:
            self.matched += 1
        elif verdict is Verdict.UNKNOWN:
            self.unknown += 1
        elif excludes:
            self.excluded += 1


@dataclass(frozen=True)
class SearchFilters:
    """Trait filters. Colour is deliberately absent — it ranks, it never excludes.

    `include_unknown` is the user's answer to "and the ones we have no record
    for?". Default false keeps the list trustworthy; the count is reported
    either way, so the choice is visible rather than made silently on their
    behalf.
    """

    height_min: float | None = None
    height_max: float | None = None
    flowering_month: int | None = None
    growth_form: str | None = None
    include_unknown: bool = False
    exclude_woody: bool = False
    exclude_introduced: bool = False
    exclude_taxa: frozenset[int] = frozenset()


def excluded_outright(plant: PlantRow, filters: SearchFilters) -> bool:
    """The category exclusions, which are not trait filters and are not counted.

    These answer "is this a candidate at all" rather than "does it match what
    was asked for": a species already in the bed, a tree in a flower bed, a
    plant the product does not promise.
    """
    if plant.taxon_id in filters.exclude_taxa:
        return True
    if filters.exclude_woody and _is_woody(plant):
        return True
    return filters.exclude_introduced and (plant.text("native_de") or "") == INTRODUCED


def _height_verdict(plant: PlantRow, filters: SearchFilters) -> Verdict | None:
    if filters.height_min is None and filters.height_max is None:
        return None
    height = plant.number("height_max_m")
    if height is None:
        return Verdict.UNKNOWN
    if filters.height_min is not None and height < filters.height_min:
        return Verdict.MISMATCH
    if filters.height_max is not None and height > filters.height_max:
        return Verdict.MISMATCH
    return Verdict.MATCH


def _flowering_verdict(plant: PlantRow, filters: SearchFilters) -> Verdict | None:
    """Wrap-aware, because 132 German species flower across the year end.

    `start <= month <= end` is False for every one of them, in every month —
    including the months they actually flower. Bergenia crassifolia runs 12 to
    7. `flowering_months` has handled this since Wave 3; re-deriving the
    comparison here is how it got derived wrong.
    """
    if filters.flowering_month is None:
        return None
    start = plant.number("flowering_start_month")
    end = plant.number("flowering_end_month")
    if start is None or end is None:
        return Verdict.UNKNOWN
    months = flowering_months(int(start), int(end))
    return Verdict.MATCH if filters.flowering_month in months else Verdict.MISMATCH


def _form_verdict(plant: PlantRow, filters: SearchFilters) -> Verdict | None:
    if filters.growth_form is None:
        return None
    form = plant.text("growth_form")
    if form is None:
        return Verdict.UNKNOWN
    return Verdict.MATCH if form.lower() == filters.growth_form.lower() else Verdict.MISMATCH


def _colour_verdict(plant: PlantRow, colour: str | None) -> Verdict | None:
    """Colour ranks; a mismatch is ordered down, never removed."""
    if colour is None:
        return None
    value = plant.text("flower_colour")
    if value is None:
        return Verdict.UNKNOWN
    return Verdict.MATCH if value.lower() == colour.lower() else Verdict.MISMATCH


def verdicts_for(
    plant: PlantRow, filters: SearchFilters, colour: str | None
) -> dict[str, Verdict]:
    """One verdict per *active* filter. Inactive filters are absent, not neutral."""
    found = {
        "height": _height_verdict(plant, filters),
        "flowering_month": _flowering_verdict(plant, filters),
        "growth_form": _form_verdict(plant, filters),
        "colour": _colour_verdict(plant, colour),
    }
    return {name: v for name, v in found.items() if v is not None}


def _is_woody(plant: PlantRow) -> bool:
    """Whether this is a tree or shrub, from whichever signal the data has.

    Three sources because no single one covers the catalogue: growth form is the
    most direct, woodiness is by far the best covered, and height catches what
    neither records. A species with none of the three is kept — absent data is
    not a property of the plant, the rule that also keeps flower colour soft.
    """
    form = plant.text("growth_form")
    if form is not None and form.lower() in WOODY_FORMS:
        return True
    if (plant.text("woodiness") or "").lower() == "woody":
        return True
    height = plant.number("height_max_m")
    return height is not None and height >= WOODY_HEIGHT_M
