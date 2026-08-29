"""The open sources this catalogue is built from, and what they permit.

Listed here rather than counted from the data because the count is a property
of the build, not of a row: GloBI supplies the interaction summaries, which
carry no source column once summarised, so counting `trait.source` would report
three sources for a catalogue built from four.

The landing page states these figures, and a page that states a number is making
a claim. This is where the claim is kept honest.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    name: str
    licence: str
    url: str
    contributes: str


SOURCES: tuple[Source, ...] = (
    Source(
        name="EIVE 1.0",
        licence="CC-BY-4.0",
        url="https://doi.org/10.14471/2022.02.001",
        contributes="Standortansprüche (Ellenberg-Zeigerwerte mit Nischenbreiten)",
    ),
    Source(
        name="GBIF",
        licence="CC-BY-4.0",
        url="https://www.gbif.org",
        contributes="Taxonomie, Vorkommen in Deutschland, deutsche Namen",
    ),
    Source(
        name="GIFT",
        licence="CC-BY-4.0",
        url="https://gift.uni-goettingen.de",
        contributes="Wuchsform, Höhe, Blütezeit und -farbe",
    ),
    Source(
        name="GloBI",
        licence="CC0-1.0",
        url="https://www.globalbioticinteractions.org",
        contributes="Beziehungen zwischen Pflanzen und Tieren",
    ),
)
