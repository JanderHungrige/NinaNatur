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
            # `[^{,]*` so an attribute or pseudo-class suffix still counts:
            # the rule that actually shipped the bug was
            # `.obstacle[role='button']:focus-visible`, and the earlier pattern
            # required the selector to end right there — so the guard was blind
            # to exactly the rule it existed for.
            rf"{re.escape(selector)}[^{{,]*(?:,[^{{]*)?\{{([^}}]*)\}}", css
        ):
            # `vector-effect: non-scaling-stroke` takes the width out of the
            # canvas's units and into the screen's, which is the right way to
            # draw something the user aims at rather than measures.
            if "non-scaling-stroke" in block:
                continue
            for prop in ("stroke-width", "outline-width", "outline"):
                for width in re.findall(rf"{prop}:\s*([0-9.]+)", block):
                    # Wider than 30 cm is a wall, not an outline. `outline` is
                    # checked too: it put a three-metre blue rectangle around
                    # every focused bed, drawn on the bounding box at that.
                    if float(width) > 0.3:
                        too_wide.append(f"{selector}: {prop} {width}")
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


def test_the_second_column_only_appears_when_both_fit() -> None:
    """Widening the window must never make the plan narrower.

    It did: the sidebar is 22rem, and the second column arrived at 60rem. One
    pixel past the breakpoint the plan dropped from 902 px to 527 — the user
    saw it as the app deciding the window had got smaller. Two columns are only
    worth it once the plan still gets a usable width.
    """
    css = STYLESHEET.read_text(encoding="utf-8")
    sidebar = re.search(r"\.layout \{[^}]*minmax\([^,]+, ([\d.]+)rem\)", css, re.S)
    breakpoint_ = re.search(r"@media \(max-width: ([\d.]+)rem\)\s*\{\s*\.layout", css)
    assert sidebar is not None and breakpoint_ is not None

    #: What the plan needs before a second column beats a single one.
    plan_minimum_rem = 40.0
    gap_rem = 1.5
    needed = float(sidebar.group(1)) + gap_rem + plan_minimum_rem
    assert float(breakpoint_.group(1)) >= needed, (
        f"two columns start at {breakpoint_.group(1)}rem but need {needed}rem"
    )


def test_the_landing_page_is_not_squeezed_into_the_garden_sidebar() -> None:
    """`.layout` is the garden's two-column grid. The landing page was rendered
    inside it, so above the breakpoint it was handed the 22rem sidebar column —
    352 px of landing page on a 1600 px window, and correct again only when the
    window was made *smaller* than the breakpoint.

    The guard is on the markup rather than the CSS: whichever way it is solved,
    a single element must not be both.
    """
    app = (
        STYLESHEET.parent / "App.tsx"
    ).read_text(encoding="utf-8")
    landing = app.index("<Landing")
    opening = app.rindex("<main", 0, landing)
    assert 'className="layout"' not in app[opening:landing], (
        "the landing page is inside the garden's two-column grid"
    )


def test_the_moving_background_stops_for_reduced_motion() -> None:
    """Feature 41 promised `prefers-reduced-motion` would be respected, and the
    drifting leaves are the first thing on the site that actually moves — the
    first time the promise costs anything.

    Stopped, not slowed: a slower animation is still an animation to somebody
    who asked the system for less motion.

    What is asserted is that the motion stops, not that the field disappears.
    The field became the hero's ground when it stopped being seven leaves over
    white, and hiding it would leave an empty dark box — which keeps neither the
    promise nor the design. The promise was never "no background".
    """
    css = STYLESHEET.read_text(encoding="utf-8")
    start = css.index("@media (prefers-reduced-motion: reduce)")
    block = css[start : css.index("\n}", css.index("{", start))]
    assert ".living" in block, "the particle field is not covered"
    assert "animation: none" in block, "the field is not actually stopped"
