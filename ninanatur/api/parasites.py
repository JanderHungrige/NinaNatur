"""Plants nobody can grow in a bed: they live on a host, or on a fungus.

The owner saw *Lathraea squamaria* offered for a sunny bed in March (review #9,
2026-09-21) — a plant with no chlorophyll that lives on the roots of hazel and
alder. Its EIVE values are real and it fits the soil perfectly; it is still no
suggestion, because it cannot be sown, planted or bought, and without its host
and its fungus it is not a plant at all.

The catalogue records no parasitism, so this is a curated list, by genus where
the whole genus is alike and by species where it is mixed. Names were checked
against the shipped catalogue on 2026-09-21.

**Left in, deliberately: the root hemiparasites** — *Rhinanthus*, *Melampyrum*,
*Euphrasia*, *Odontites*, *Pedicularis*, *Thesium*. They are green, they are
sown, and *Rhinanthus* is sown into meadows on purpose to weaken the grass. So
the rule is not "Orobanchaceae": most of that family is in this second group.
"""
from __future__ import annotations

#: Every species of these lives on a host or a fungus.
PARASITIC_GENERA: frozenset[str] = frozenset({
    # Holoparasites: no chlorophyll, on the roots or stems of a host.
    "Orobanche",    # broomrapes
    "Phelipanche",  # the branched broomrapes, split from Orobanche
    "Lathraea",     # toothworts, on hazel, alder, poplar
    "Cuscuta",      # dodders, twining over their host
    # Mycoheterotrophs: fed by a fungus rather than by light.
    "Monotropa",    # Monotropa hypopitys, as some checklists still name it
    "Hypopitys",    # yellow bird's-nest
    "Epipogium",    # ghost orchid
    "Corallorhiza",  # coralroot, almost without chlorophyll
    "Limodorum",    # violet limodore, too little leaf to live on
    # Aerial parasites, on the branches of trees.
    "Viscum",       # mistletoe
    "Loranthus",    # oak mistletoe
})

#: Where a genus is mixed. *Neottia ovata* and *N. cordata* — the former
#: *Listera* — are green orchids and stay; the bird's-nest orchid is not.
#: "Neottia nidus" is how the catalogue also carries it, a name cut short at
#: the hyphen.
PARASITIC_SPECIES: frozenset[str] = frozenset({
    "Neottia nidus-avis",
    "Neottia nidus",
})


def is_parasitic(canonical_name: str) -> bool:
    """Whether this species lives on a host or a fungus, by its name."""
    name = canonical_name.strip()
    genus = name.split(" ", 1)[0]
    return genus in PARASITIC_GENERA or name in PARASITIC_SPECIES


__all__ = ["PARASITIC_GENERA", "PARASITIC_SPECIES", "is_parasitic"]
