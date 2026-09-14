"""The garden as a workspace: the window's height, and only panels scroll.

Wave 23, feature 1 (doc 87). Read as text, like the sheet's other guards —
jsdom lays nothing out, so the rules that decide whether the page scrolls are
visible only in the CSS.
"""
import re
from pathlib import Path

import pytest

STYLESHEET = Path("frontend/src/styles.css")
SRC = Path("frontend/src")

RAIL_REM = 3.5
INSPECTOR_REM = 22.0
WIDE_INSPECTOR_REM = 30.0
#: What the plan needs before a third column beats a stacked page.
PLAN_MINIMUM_REM = 40.0


@pytest.fixture(scope="module")
def css() -> str:
    text = STYLESHEET.read_text(encoding="utf-8")
    assert len(text) > 1000, f"{STYLESHEET} looks empty — the test would be vacuous"
    # Comments out first: a rule described in a comment is not a rule.
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def _min_width_blocks(css: str) -> list[tuple[float, str]]:
    """Every top-level `@media (min-width: Nrem)` block, with N and its body."""
    pattern = r"^@media \(min-width: ([\d.]+)rem\) \{(.*?)^\}"
    return [(float(size), body) for size, body in re.findall(pattern, css, re.S | re.M)]


def _where(css: str, selector: str) -> tuple[float, str]:
    """The min-width block that styles `selector`, and that rule's body."""
    rule = rf"^\s*{re.escape(selector)}\s*\{{([^}}]*)\}}"
    for size, body in _min_width_blocks(css):
        found = re.search(rule, body, re.M)
        if found is not None:
            return size, found.group(1)
    raise AssertionError(f"no @media (min-width) block styles {selector}")


def test_the_workspace_only_opens_when_the_plan_keeps_its_width(css: str) -> None:
    """Widening the window must never make the plan narrower.

    It did once: the two-column layout's second column arrived while the plan
    had no room for it, and one pixel past the breakpoint the plan dropped from
    902 px to 527 — which reads exactly like the app deciding the window got
    smaller. A third column is only worth it once the plan still gets 40rem.
    """
    size, rule = _where(css, ".workspace")
    columns = re.search(r"grid-template-columns:\s*([^;]+);", rule)
    assert columns is not None, ".workspace sets no columns"
    assert re.sub(r"\s+", " ", columns.group(1).strip()) == "3.5rem minmax(0, 1fr) 22rem"
    assert size >= RAIL_REM + INSPECTOR_REM + PLAN_MINIMUM_REM


def test_the_wide_inspector_waits_for_the_room_it_takes(css: str) -> None:
    size, rule = _where(css, ".workspace--wide")
    assert "30rem" in rule
    assert size >= RAIL_REM + WIDE_INSPECTOR_REM + PLAN_MINIMUM_REM


def test_the_workspace_is_the_window_and_only_panels_scroll(css: str) -> None:
    _, app = _where(css, ".app--workspace")
    assert "height: 100vh" in app and "height: 100dvh" in app
    assert app.index("100vh") < app.index("100dvh"), "the fallback has to come first"
    _, body = _where(css, "body:has(.app--workspace)")
    assert "padding: 0" in body, "the body's padding would make the page taller than the window"
    _, inspector = _where(css, ".inspector")
    for declaration in ("overflow-y: auto", "overscroll-behavior: contain", "min-height: 0"):
        assert declaration in inspector, declaration
    _, plan = _where(css, ".workspace__plan")
    assert "min-width: 0" in plan and "min-height: 0" in plan


def test_the_stage_fills_the_plan_cell_in_the_workspace(css: str) -> None:
    """The plan's height still comes from the page and never from the drawing
    (doc 86) — in the workspace, from the grid row it is given."""
    _, stage = _where(css, ".workspace .canvas-stage")
    assert "height: 100%" in stage


def test_the_dock_leaves_the_plan_its_share(css: str) -> None:
    """At most 40vh of dock, so the plan keeps at least 40 % with it open."""
    _, dock = _where(css, ".timeline-dock__body")
    limit = re.search(r"max-height:\s*([\d.]+)vh", dock)
    assert limit is not None and float(limit.group(1)) <= 40
    assert "overflow-y: auto" in dock


def test_a_fresh_patch_holds_still_for_reduced_motion(css: str) -> None:
    """Doc 88: *Pflanzen* marks the patch with a pulse, and with a still ring for
    anyone who asked for less motion."""
    assert re.search(r"\.cluster--fresh[^{]*\{[^}]*animation:", css), "no pulse"
    reduced = r"@media \(prefers-reduced-motion: reduce\) \{(.*?)^\}"
    blocks = re.findall(reduced, css, re.S | re.M)
    assert blocks, "the sheet has no reduced-motion block"
    stopped = r"\.cluster--fresh[^{]*\{[^}]*animation:\s*none"
    assert any(re.search(stopped, block) for block in blocks), (
        "the pulse keeps running under prefers-reduced-motion"
    )


def test_the_tabs_are_gone() -> None:
    """Zeichnen and Säen were two ends of one loop; the inspector replaces them."""
    assert not (SRC / "components" / "Tabs.tsx").exists()
    assert "tabs__" not in STYLESHEET.read_text(encoding="utf-8")
    assert "components/Tabs" not in (SRC / "App.tsx").read_text(encoding="utf-8")
