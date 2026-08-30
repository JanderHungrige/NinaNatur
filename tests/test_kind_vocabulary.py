"""The German vocabulary lives in the frontend; the kinds live here.

Two lists that must agree, in different languages, checked by neither compiler.
This is the guard. It exists because the object editor offered "Gebäude" for as
long as it kept its own copy — a dropdown writing a kind the server had already
replaced, which fails only when somebody saves.
"""
from __future__ import annotations

import re
from pathlib import Path

from ninanatur.garden.objects import TRAITS, ObjectKind

KINDS_TS = Path(__file__).resolve().parents[1] / "frontend" / "src" / "kinds.ts"


def _kinds_in_frontend() -> list[str]:
    source = KINDS_TS.read_text(encoding="utf-8")
    body = source[source.index("export const KINDS") : source.index("export const STANDING")]
    return re.findall(r"\{ kind: '([a-z]+)'", body)


def test_frontend_names_every_kind_the_server_has() -> None:
    assert set(_kinds_in_frontend()) == {k.value for k in ObjectKind}


def test_frontend_agrees_on_which_kinds_stand_up() -> None:
    """Standing decides two things at once: what casts a shadow, and what is
    drawn on top. A surface listed as standing would darken a terrace."""
    source = KINDS_TS.read_text(encoding="utf-8")
    for kind, traits in TRAITS.items():
        entry = re.search(rf"\{{ kind: '{kind.value}',.*?standing: (true|false)", source)
        assert entry is not None, f"{kind.value} missing from kinds.ts"
        assert (entry.group(1) == "true") is traits.casts_shadow


def test_frontend_agrees_on_starting_heights() -> None:
    source = KINDS_TS.read_text(encoding="utf-8")
    for kind, traits in TRAITS.items():
        entry = re.search(rf"\{{ kind: '{kind.value}',.*?height: ([\d.]+|null)", source)
        assert entry is not None, f"{kind.value} missing from kinds.ts"
        shown = None if entry.group(1) == "null" else float(entry.group(1))
        assert shown == traits.height, f"{kind.value}: {shown} vs {traits.height}"


def test_frontend_agrees_on_what_each_kind_is_drawn_as() -> None:
    """The symbol decides the texture. A kind whose symbol drifts is drawn as
    something else entirely — paving as water, and nobody sees a stack trace."""
    source = KINDS_TS.read_text(encoding="utf-8")
    for kind, traits in TRAITS.items():
        entry = re.search(rf"\{{ kind: '{kind.value}',.*?symbol: '([a-z]+)'", source)
        assert entry is not None, f"{kind.value} has no symbol in kinds.ts"
        assert entry.group(1) == traits.symbol
