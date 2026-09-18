"""Every theme's marks say whose they are (doc 96).

Draft Sketch is used and adapted with Warren Davison's written permission, and
extended in his hand. A plan that mixes his marks, adaptations of them and our
own has to be able to say which is which, file by file — so every theme's
symbol file opens with a comment naming its author, in one of four agreed
forms, and a file without one is refused here rather than argued about later.
"""
from __future__ import annotations

import re
from pathlib import Path

THEMES = Path(__file__).resolve().parents[1] / "frontend" / "src" / "themes"

ALLOWED = frozenset({
    "NinaNatur",
    "Warren Davison (Draft Sketch)",
    "adapted from Draft Sketch",
    "NinaNatur, in the style of Draft Sketch",
})

_HEADER = re.compile(r"^\s*(?:<\?xml[^>]*>\s*)?(?:/\*|<!--)(?P<body>.*?)(?:\*/|-->)", re.S)
_LINE = re.compile(r"Provenance:\s*(?P<who>[^\n]+?)\s*$", re.M)


def provenance_of(text: str) -> str | None:
    """The author a file's opening comment names, or None if it names nobody."""
    head = _HEADER.match(text)
    if head is None:
        return None
    found = _LINE.search(head.group("body"))
    return None if found is None else found.group("who").strip(" *")


def symbol_files() -> list[Path]:
    return sorted(
        path for path in THEMES.glob("*/*")
        if path.name.startswith("symbols.") or path.suffix == ".svg"
    )


def test_every_theme_has_its_marks_in_a_symbol_file() -> None:
    themes = sorted(p.name for p in THEMES.iterdir() if p.is_dir())
    assert "technisch" in themes
    for theme in themes:
        assert any(f.parent.name == theme for f in symbol_files()), f"{theme} has no symbols file"


def test_every_symbol_file_says_whose_marks_it_holds() -> None:
    for path in symbol_files():
        who = provenance_of(path.read_text(encoding="utf-8"))
        assert who in ALLOWED, f"{path.relative_to(THEMES)}: provenance {who!r}"


def test_a_file_that_names_nobody_is_refused() -> None:
    assert provenance_of("export function Symbols() {}\n") is None
    assert provenance_of("/* The plan's patterns. */\nexport const x = 1;\n") is None
    # A header further down is not the file's header.
    assert provenance_of("const a = 1;\n/* Provenance: NinaNatur */\n") is None


def test_only_the_agreed_words_count() -> None:
    assert provenance_of("/*\n * Provenance: NinaNatur\n */\n") == "NinaNatur"
    assert provenance_of("<!-- Provenance: Warren Davison (Draft Sketch) -->") in ALLOWED
    assert provenance_of("/* Provenance: somebody on the internet */") not in ALLOWED
