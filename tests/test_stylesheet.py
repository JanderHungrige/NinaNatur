"""The stylesheet's own consistency.

Checked from here rather than from vitest, which stubs CSS imports: reading the
sheet with `?raw` returns an empty string, and a test over nothing passes every
assertion. Giving vitest filesystem types instead meant adding @types/node,
which broke the type resolution of @testing-library/react across the suite. The
rule under test is a text property of a file, and this suite already reads files.
"""
import re
from pathlib import Path

import pytest

STYLESHEET = Path("frontend/src/styles.css")

# Custom properties set from TypeScript rather than declared in the sheet.
SET_INLINE = frozenset({"--fill"})

# Not a colour, so it needs no dark-mode counterpart.
NOT_A_COLOUR = frozenset({"--radius"})


@pytest.fixture(scope="module")
def css() -> str:
    text = STYLESHEET.read_text(encoding="utf-8")
    # Guards every assertion below: an empty read satisfies all of them.
    assert len(text) > 1000, f"{STYLESHEET} looks empty — the test would be vacuous"
    return text


def _declared(css: str) -> set[str]:
    return set(re.findall(r"^\s*(--[a-z0-9-]+)\s*:", css, re.M))


def _used(css: str) -> set[str]:
    return set(re.findall(r"var\((--[a-z0-9-]+)", css))


def test_the_sheet_declares_a_palette_and_uses_it(css: str) -> None:
    assert len(_declared(css)) > 5
    assert len(_used(css)) > 5


def test_every_variable_used_is_declared(css: str) -> None:
    """CSS fails silently, which is what makes this worth a test.

    An undeclared variable falls back to whatever literal follows the comma, so
    `var(--surface-2, #eef3ec)` painted a light green chip in dark mode and left
    near-white text on it. Nothing errors and nothing logs; it is visible only
    by looking, and only in one theme. Four invented names shipped this way.
    """
    unknown = sorted(_used(css) - _declared(css) - SET_INLINE)
    assert unknown == [], f"used but never declared: {unknown}"


def test_every_colour_has_a_dark_mode_value(css: str) -> None:
    """A colour declared only in :root keeps its light value in dark mode — the
    same unreadable result reached by a different route."""
    dark = css[css.index("@media (prefers-color-scheme: dark)") :]
    missing = sorted(
        name
        for name in _declared(css)
        if name not in NOT_A_COLOUR and name not in SET_INLINE and f"{name}:" not in dark
    )
    assert missing == [], f"no dark-mode value: {missing}"


# Selectors that style the garden plan. Its viewBox is in **garden metres**
# since Wave 7, so every length here is metres too.
PLAN_SELECTORS = (".grid-line", ".bed", ".bed--selected", ".obstacle", ".draft__line")


def test_plan_strokes_are_measured_in_metres(css: str) -> None:
    """These were pixel values under the old ten-pixels-per-metre viewBox.

    Wave 7 moved the plan into metres and left them behind, so `stroke-width: 2`
    became a two-metre outline: it painted a metre outside a 4 m bed on every
    side and swallowed most of the shape, and the 1 m grid rendered as a field
    of blocks. Visible in every screenshot and registered in none of them.
    """
    too_wide: list[str] = []
    for selector in PLAN_SELECTORS:
        for block in re.findall(
            rf"{re.escape(selector)}\s*(?:,[^{{]*)?\{{([^}}]*)\}}", css
        ):
            for width in re.findall(r"stroke-width:\s*([0-9.]+)", block):
                # A stroke wider than 30 cm is a wall, not an outline.
                if float(width) > 0.3:
                    too_wide.append(f"{selector}: {width}")
    assert too_wide == [], f"stroke widths look like pixels, not metres: {too_wide}"


def test_obstacle_rule_declares_no_fill() -> None:
    """The fill is a per-object attribute naming that kind's texture, and a
    `fill` in CSS beats a presentation attribute. One declaration here would
    draw every kind as the same grey while the markup still asked for slabs,
    water and foliage — and the tests asserting on the attribute would pass."""
    css = STYLESHEET.read_text(encoding="utf-8")
    rule = re.search(r"^\.obstacle \{([^}]*)\}", css, re.M)
    assert rule is not None, ".obstacle rule not found"
    assert "fill" not in rule.group(1)
