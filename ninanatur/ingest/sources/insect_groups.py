"""Which insects are bees, which are butterflies, which are hoverflies.

Wave 2 built the German checklist from GBIF's name facet — 19 requests instead of
19,000 — and in doing so dropped family and order. The same trick recovers the
groups without giving the saving back: one facet per clade, eight calls in total.
"""
from __future__ import annotations

import sqlite3
from enum import Enum

from ninanatur.ingest.sources.base import finish_run, start_run
from ninanatur.ingest.sources.gbif import canonical_name, fetch_german_scientific_names

SOURCE_NAME = "GBIF-insect-groups"
LICENSE = "CC-BY-4.0"


class InsectGroup(Enum):
    """Groups a gardener recognises, not a taxonomy."""

    BEE = "bee"
    BUTTERFLY = "butterfly"
    HOVERFLY = "hoverfly"


# Bees are taken by family: the superfamily key is ambiguous — "Apoidea" matches
# only fuzzily, and to a genus. Six exact family matches beat one uncertain
# superfamily.
GROUP_CLADES: dict[InsectGroup, tuple[int, ...]] = {
    InsectGroup.BEE: (4334, 7901, 7908, 7911, 7905, 4345),
    InsectGroup.BUTTERFLY: (797,),
    InsectGroup.HOVERFLY: (6920,),
}


def apply_groups(
    conn: sqlite3.Connection, members: dict[InsectGroup, set[str]]
) -> int:
    """Label the German checklist with its groups. Returns rows updated.

    A species appearing in two groups means the clade facets overlap, which is a
    data problem worth seeing rather than a last-write-wins to shrug at.
    """
    seen: dict[str, InsectGroup] = {}
    for group, names in members.items():
        for name in names:
            previous = seen.get(name)
            if previous is not None and previous is not group:
                raise ValueError(
                    f"{name!r} appears in more than one group: "
                    f"{previous.value} and {group.value}"
                )
            seen[name] = group

    updated = 0
    for name, group in seen.items():
        cursor = conn.execute(
            "UPDATE insect_de SET insect_group = ? WHERE canonical_name = ?",
            (group.value, name),
        )
        updated += cursor.rowcount
    conn.commit()
    return updated


class InsectGroupsSource:
    """Classifies the German insect checklist by clade."""

    name = SOURCE_NAME
    license = LICENSE

    def run(self, conn: sqlite3.Connection, limit: int | None = None) -> int:
        started = start_run(conn, self.name)
        members: dict[InsectGroup, set[str]] = {}
        for group, clades in GROUP_CLADES.items():
            names: set[str] = set()
            for clade in clades:
                raw = fetch_german_scientific_names(clade)
                names |= {
                    canonical
                    for canonical in (canonical_name(n) for n in raw)
                    if " " in canonical
                }
            members[group] = names
            print(f"  {group.value}: {len(names)} German species", flush=True)

        updated = apply_groups(conn, members)
        finish_run(conn, self.name, started, updated, "complete")
        return updated
