"""Candidate loading, filtering and ranking for plant search.

Kept out of the route layer: the route's job is parameters in, schema out, and
this is where the actual decision about what matches lives.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ninanatur.fit.score import AXES, FitResult, SiteVector, SpeciesNiche, score_species

# Query parameter -> canonical axis. Gardeners think "light", the data says
# "ellenberg_l"; the translation belongs here and nowhere else.
AXIS_PARAMS: dict[str, str] = {
    "light": "ellenberg_l",
    "moisture": "ellenberg_m",
    "nutrients": "ellenberg_n",
    "reaction": "ellenberg_r",
    "temperature": "ellenberg_t",
}


@dataclass(frozen=True)
class PlantRow:
    """One candidate: identity, indicator niche, and the traits shown in a list."""

    taxon_id: int
    canonical_name: str
    family: str | None
    niche: SpeciesNiche
    extras: dict[str, float | str] = field(default_factory=dict)

    def number(self, key: str) -> float | None:
        value = self.extras.get(key)
        return float(value) if isinstance(value, (int, float)) else None

    def text(self, key: str) -> str | None:
        value = self.extras.get(key)
        return str(value) if isinstance(value, str) else None


@dataclass(frozen=True)
class ScoredPlant:
    """A candidate with its fit — typed, so the ranking code needs no casts."""

    plant: PlantRow
    fit: FitResult

    @property
    def score(self) -> float:
        return self.fit.score or 0.0


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


@dataclass(frozen=True)
class SearchFilters:
    """Hard filters. Colour is deliberately absent — it ranks, it never excludes."""

    height_min: float | None = None
    height_max: float | None = None
    flowering_month: int | None = None
    exclude_woody: bool = False
    exclude_introduced: bool = False
    exclude_taxa: frozenset[int] = frozenset()


def load_candidates(conn: sqlite3.Connection) -> list[PlantRow]:
    """Load the whole German candidate set in one query.

    Per-species queries would be thousands of round trips for a single search.
    """
    rows = conn.execute(
        """
        SELECT x.taxon_id, x.canonical_name, x.family, t.trait_key, t.value_num, t.value_text
        FROM taxon x LEFT JOIN trait t ON t.taxon_id = x.taxon_id
        WHERE x.occurs_de = 1
        """
    ).fetchall()

    values: dict[int, dict[str, float | None]] = {}
    widths: dict[int, dict[str, float | None]] = {}
    extras: dict[int, dict[str, float | str]] = {}
    names: dict[int, tuple[str, str | None]] = {}

    for row in rows:
        tid = int(row["taxon_id"])
        names.setdefault(tid, (row["canonical_name"], row["family"]))
        key = row["trait_key"]
        if key is None:
            continue
        if key in AXES:
            values.setdefault(tid, {})[key] = row["value_num"]
        elif key.endswith("_nw"):
            widths.setdefault(tid, {})[key[:-3]] = row["value_num"]
        elif row["value_num"] is not None:
            extras.setdefault(tid, {})[key] = float(row["value_num"])
        elif row["value_text"] is not None:
            extras.setdefault(tid, {})[key] = str(row["value_text"])

    return [
        PlantRow(
            taxon_id=tid,
            canonical_name=name,
            family=family,
            niche=SpeciesNiche(tid, values.get(tid, {}), widths.get(tid, {})),
            extras=extras.get(tid, {}),
        )
        for tid, (name, family) in names.items()
    ]


def _passes(plant: PlantRow, filters: SearchFilters) -> bool:
    if plant.taxon_id in filters.exclude_taxa:
        return False
    if filters.exclude_woody and _is_woody(plant):
        return False
    if filters.exclude_introduced and (plant.text("native_de") or "") == INTRODUCED:
        return False
    height = plant.number("height_max_m")
    if filters.height_min is not None and (height is None or height < filters.height_min):
        return False
    if filters.height_max is not None and (height is None or height > filters.height_max):
        return False
    if filters.flowering_month is not None:
        start = plant.number("flowering_start_month")
        end = plant.number("flowering_end_month")
        if start is None or end is None or not start <= filters.flowering_month <= end:
            return False
    return True


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


def _colour_rank(plant: PlantRow, colour: str | None) -> int:
    """Known match, then unknown, then known mismatch.

    Colour ranks rather than excludes: dropping unknowns would hide the ~88% of
    the catalogue whose colour was never recorded, which is a data gap, not a
    property of the plant.
    """
    if colour is None:
        return 0
    value = plant.text("flower_colour")
    if value is None:
        return 1
    return 0 if value.lower() == colour.lower() else 2


def rank_plants(
    candidates: list[PlantRow],
    site: SiteVector,
    filters: SearchFilters,
    colour: str | None = None,
) -> list[ScoredPlant]:
    """Score, filter and order candidates against one bed."""
    scored: list[ScoredPlant] = []
    for plant in candidates:
        if not _passes(plant, filters):
            continue
        fit = score_species(site, plant.niche)
        if fit.score is None:
            continue
        scored.append(ScoredPlant(plant=plant, fit=fit))

    scored.sort(key=lambda s: (_colour_rank(s.plant, colour), -s.score))
    return scored
