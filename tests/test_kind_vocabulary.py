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


ROOFS_TS = KINDS_TS.with_name("roofs.ts")


def test_frontend_offers_exactly_the_roof_shapes_the_model_knows() -> None:
    """`roofs.ts` has said since Wave 16 that a guard held it to the server's
    list. None did until Wave 21 — the only check compared two Python lists."""
    from ninanatur.garden.roofs import Roof

    source = ROOFS_TS.read_text(encoding="utf-8")
    body = source[source.index("export const ROOFS") : source.index("export const ROOFED")]
    assert set(re.findall(r"\['([a-z]+)', '", body)) == {r.value for r in Roof}


def test_frontend_assumes_the_eaves_where_the_model_does() -> None:
    """The page says what the model assumed for eaves nobody gave (doc 93), so
    it has to assume the same thing."""
    from ninanatur.garden.roofs import DEFAULT_EAVES_FRACTION

    source = ROOFS_TS.read_text(encoding="utf-8")
    entry = re.search(r"export const EAVES_FRACTION = ([\d.]+);", source)
    assert entry is not None, "roofs.ts no longer says where it puts the eaves"
    assert float(entry.group(1)) == DEFAULT_EAVES_FRACTION
