"""The plan's rules in the stylesheet, from the owner's check of 2026-09-21.

Split from `test_stylesheet.py`, which the check's additions took past the
300-line limit. Read as text for the same reason that file gives: vitest stubs
CSS imports, so a test there would assert over an empty string.
"""
import re
from pathlib import Path

STYLESHEET = Path("frontend/src/styles.css")
SKETCH = Path("frontend/src/themes/draft-sketch/theme.css")


def _rule(css: str, selector: str) -> str:
    """The body of the first top-level rule for exactly this selector."""
    found = re.search(rf"^{re.escape(selector)} \{{([^}}]*)\}}", css, re.M)
    assert found is not None, f"no rule for {selector}"
    return found.group(1)


def test_plan_outlines_are_screen_pixels_at_every_zoom() -> None:
    """A width in metres grew with the zoom, to forty pixels at the closest
    view (#1). Each outline is a pixel width held by non-scaling-stroke; a
    pixel number without it would be read as metres, and vanish."""
    css = STYLESHEET.read_text(encoding="utf-8")
    for selector in (".bed", ".bed--selected", ".obstacle", ".obstacle--garden", ".draft__line"):
        body = _rule(css, selector)
        width = re.search(r"stroke-width:\s*([\d.]+)", body)
        assert width is not None, f"{selector} has no stroke width"
        assert float(width.group(1)) >= 1, f"{selector} is still in metres"
        assert "vector-effect: non-scaling-stroke" in body, f"{selector} scales with the zoom"


def test_the_costly_paint_pauses_while_the_plan_moves() -> None:
    """#11: the watercolour filter, his paper and his splotches are what a pan
    frame cost. `useMoving` sets the class; these rules are what it switches."""
    css = STYLESHEET.read_text(encoding="utf-8")
    assert "filter: none" in _rule(css, ".canvas--moving .canvas__objects")
    sketch = SKETCH.read_text(encoding="utf-8")
    moving = ".canvas--moving .plan-theme--draft-sketch"
    assert "display: none" in _rule(sketch, f"{moving} .canvas__paper")
    assert "mask: none" in _rule(sketch, f"{moving} .bloom-dot")


def test_the_gardens_ground_is_a_flat_grass_wash() -> None:
    """A 5 % tint left the plan nearly white where it opens (owner's check,
    2026-09-21). Flat, not a pattern: the blades are a drawn lawn's, and the two
    must still tell apart. More contrast takes it away with every other fill."""
    css = STYLESHEET.read_text(encoding="utf-8")
    rule = re.search(r"^\.obstacle--garden \{([^}]*)\}", css, re.M)
    assert rule is not None, ".obstacle--garden rule not found"
    fill = re.search(r"\bfill:\s*([^;]+);", rule.group(1))
    assert fill is not None and "--wash-grass" in fill.group(1) and "url(" not in fill.group(1)
    contrast = css[css.index("@media (prefers-contrast: more)"):]
    assert re.search(r"\.obstacle \{[^}]*fill: none !important", contrast)


def test_the_waiting_marks_stand_still_for_reduced_motion() -> None:
    """Every sign that something is under way turns, rises, breathes or sweeps
    (doc 87) — and every one of them must stop for somebody who asked their
    system for less motion. Stopped, and still there: a still ring, still motes
    and grey bars still say "under way"."""
    css = STYLESHEET.read_text(encoding="utf-8")
    start = css.index("@media (prefers-reduced-motion: reduce)")
    block = css[start : css.index("\n}", css.index("{", start))]
    stopped = re.search(r"([^{}]*\.working__spinner[^{}]*)\{([^}]*)\}", block)
    assert stopped is not None, "the waiting marks are not in the reduced-motion block"
    assert "animation: none" in stopped.group(2), "the waiting marks are not stopped"
    for mark in (".working__spinner", ".working__motes > span", ".skeleton__line",
                 ".stat__pending", ".plan-working::before"):
        assert mark in stopped.group(1), f"{mark} keeps moving under reduced motion"


def test_what_lies_over_the_plan_while_it_waits_takes_no_pointer() -> None:
    """The rebuild's sweep and the header's note lie over things people aim at;
    like the tool hint, they must never catch the click meant for the plan."""
    css = STYLESHEET.read_text(encoding="utf-8")
    for selector in (".plan-working", ".site-header__working", ".hero__opening"):
        body = re.search(rf"^{re.escape(selector)} \{{([^}}]*)\}}", css, re.M)
        assert body is not None, f"no rule for {selector}"
        assert "pointer-events: none" in body.group(1), f"{selector} catches the pointer"
