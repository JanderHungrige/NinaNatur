"""Loading the candidate set, and the row shape everything downstream reads.

One query for the whole German catalogue: per-species lookups would be thousands
of round trips for a single search.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ninanatur.fit.score import AXES, FitResult, SpeciesNiche

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
