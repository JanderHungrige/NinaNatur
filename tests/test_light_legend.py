"""The sun map's legend and the hours->L convention name the same places.

The map says "Halbschatten" from 2.5 h; the suggestions rank by a light value
that `solar/light.py` draws through anchors at the same hours. Until 2026-09-21
the map's comment claimed to mirror the server's table while calling 6–8 h
"volle Sonne" where the table said "sunny" — and nothing held them together.
"""
from __future__ import annotations

import re
from pathlib import Path

from ninanatur.solar import light
from ninanatur.solar.light import SUN_HOUR_ANCHORS

ROOT = Path(__file__).resolve().parents[1]
SUN_MAP = ROOT / "frontend" / "src" / "components" / "SunMap.tsx"


def _legend() -> dict[float, str]:
    """`BANDS` from the map, as hours -> name."""
    source = SUN_MAP.read_text(encoding="utf-8")
    block = source.split("export const BANDS", 1)[1].split("];", 1)[0]
    return {float(h): name for h, name in re.findall(r"\[(\d+(?:\.\d+)?), '([^']+)'\]", block)}


def _anchor_words() -> dict[float, str]:
    """The word each anchor's comment gives it, as hours -> name."""
    source = Path(light.__file__).read_text(encoding="utf-8")
    return {
        float(h): name.strip()
        for h, name in re.findall(r"\((\d+\.\d+), \d+\.\d+\),\s+# (.+?) —", source)
    }


def test_the_legend_was_read() -> None:
    assert len(_legend()) == 5
    assert len(_anchor_words()) == len(SUN_HOUR_ANCHORS)


def test_every_legend_band_begins_at_an_anchor() -> None:
    anchors = {hours for hours, _ in SUN_HOUR_ANCHORS}
    assert set(_legend()) <= anchors


def test_the_legend_and_the_anchors_use_the_same_words() -> None:
    words = _anchor_words()
    for hours, name in _legend().items():
        assert words[hours] == name, f"{hours} h"
