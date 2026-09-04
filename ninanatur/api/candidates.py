"""Loading the candidate set, and the row shape everything downstream reads.

One query for the whole German catalogue: per-species lookups would be thousands
of round trips for a single search.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from ninanatur.data.traits import source_rank
from ninanatur.fit.score import AXES, FitResult, SpeciesNiche

# Where a gardener's own answer about a species is carried through the ranking,
# alongside the catalogue's rather than over it.
OBSERVED_COLOUR = "observed_colour"

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

    def colour(self) -> str | None:
        """The colour to judge this plant by.

        One answer now, not two. A hand entry is a `trait` row marked `manual`
        and `load_candidates` has already ranked it against every published
        source — so `flower_colour` *is* the resolved colour, and preferring the
        hand entry here would put it back in front of the data that beat it.
        """
        return self.text("flower_colour")

    def number(self, key: str) -> float | None:
        value = self.extras.get(key)
        return float(value) if isinstance(value, int | float) else None

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


def load_candidates(conn: sqlite3.Connection) -> list[PlantRow]:
    """Load the whole German candidate set in one query.

    Per-species queries would be thousands of round trips for a single search.
    """
    rows = conn.execute(
        """
        SELECT x.taxon_id, x.canonical_name, x.family,
               t.trait_key, t.value_num, t.value_text, t.source
        FROM taxon x LEFT JOIN trait t ON t.taxon_id = x.taxon_id
        WHERE x.occurs_de = 1
        """
    ).fetchall()

    values: dict[int, dict[str, float | None]] = {}
    widths: dict[int, dict[str, float | None]] = {}
    extras: dict[int, dict[str, float | str]] = {}
    names: dict[int, tuple[str, str | None]] = {}
    #: The rank of the source each value came from, so a better one can replace
    #: it and a worse one cannot.
    ranks: dict[int, dict[str, tuple[int, str]]] = {}

    for row in rows:
        tid = int(row["taxon_id"])
        names.setdefault(tid, (row["canonical_name"], row["family"]))
        key = row["trait_key"]
        if key is None:
            continue
        # Two sources can now claim the same key for the same species: a hand
        # entry and whatever the catalogue holds. This loop used to let the last
        # row win, which was harmless only because EIVE and GIFT overlap in no
        # keys at all — the suggestion list would otherwise show whichever row
        # SQLite happened to return last.
        rank = source_rank(row["source"] or "")
        if key in AXES:
            if _better(ranks, tid, key, rank):
                values.setdefault(tid, {})[key] = row["value_num"]
        elif key.endswith("_nw"):
            if _better(ranks, tid, key, rank):
                widths.setdefault(tid, {})[key[:-3]] = row["value_num"]
        elif row["value_num"] is not None and _better(ranks, tid, key, rank):
            extras.setdefault(tid, {})[key] = float(row["value_num"])
        elif row["value_text"] is not None and _better(ranks, tid, key, rank):
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


def with_observed(
    candidates: list[PlantRow], observed: Mapping[int, str]
) -> list[PlantRow]:
    """Lay one garden's own flower colours over the catalogue's.

    The gardener looked at the photograph and answered a question the catalogue
    could not: colour is recorded for 590 of 8,939 species. From here on that
    answer is the plant's colour — it is what the list shows, what the colour
    filter matches, and what the "unknown" count stops counting.

    It is kept under its own key rather than written over `flower_colour`, so
    that both answers survive to the client: the list can mark which one it is
    showing, and the info panel can still say what the catalogue holds.

    Rows are replaced, not mutated. The candidate set describes the catalogue,
    which is shared by every garden and re-synced from the image; writing one
    gardener's observation into it would show up in a stranger's plan.
    """
    if not observed:
        return candidates
    return [
        replace(
            plant, extras={**plant.extras, OBSERVED_COLOUR: observed[plant.taxon_id]}
        )
        if plant.taxon_id in observed
        else plant
        for plant in candidates
    ]


def _better(
    ranks: dict[int, dict[str, tuple[int, str]]],
    taxon_id: int,
    key: str,
    rank: tuple[int, str],
) -> bool:
    """Whether this row's source beats whatever has been kept for this key.

    Records the winner as a side effect, so the caller can write the value.
    Mirrors `traits._resolve_group`, which does the same thing one species at a
    time; this is the bulk path and the two must agree.
    """
    kept = ranks.setdefault(taxon_id, {}).get(key)
    if kept is not None and kept <= rank:
        return False
    ranks[taxon_id][key] = rank
    return True
