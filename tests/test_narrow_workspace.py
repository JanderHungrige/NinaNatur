"""The narrow workspace: a phone's garden is the window, not a page (doc 91).

Read as text, like the stylesheet's other guards: jsdom lays nothing out, so
what decides whether a phone's page scrolls is visible only in the CSS.
Measured before this feature on the preview (V0.20.171), with an iPhone 11
Pro's 375×635 window: the garden was a page of 3,069 px, and the plan and the
first suggestion were 1,199 px of scrolling apart.
"""
import re
from pathlib import Path

import pytest

STYLESHEET = Path("frontend/src/styles.css")
SHEET = Path("frontend/src/workspace/sheet.ts")
SHEET_HEIGHT = r"height:\s*calc\(var\(--sheet-drag,\s*var\(--sheet-at\)\)\s*\*\s*100%\)"
LABEL_UPWARD = r"\.tool-rail__label\s*\{[^}]*bottom:\s*calc\(100% \+"


@pytest.fixture(scope="module")
def css() -> str:
    text = STYLESHEET.read_text(encoding="utf-8")
    assert len(text) > 1000, f"{STYLESHEET} looks empty — the test would be vacuous"
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


@pytest.fixture(scope="module")
def narrow(css: str) -> str:
    blocks = re.findall(r"^@media \(width < 66rem\) \{(.*?)^\}", css, re.S | re.M)
    assert len(blocks) == 1, f"expected one narrow block, found {len(blocks)}"
    return blocks[0]


def _rule(block: str, selector: str) -> str:
    found = re.search(rf"^\s*{re.escape(selector)}\s*\{{([^}}]*)\}}", block, re.M)
    assert found is not None, f"nothing styles {selector}"
    return found.group(1)


def test_the_narrow_workspace_is_the_window(narrow: str) -> None:
    app = _rule(narrow, ".app--workspace")
    assert "height: 100vh" in app and "height: 100dvh" in app
    assert app.index("100vh") < app.index("100dvh"), "the fallback has to come first"
    assert "padding: 0" in _rule(narrow, "body:has(.app--workspace)")
    workspace = _rule(narrow, ".workspace")
    for declaration in ("position: relative", "flex: 1 1 0", "min-height: 0"):
        assert declaration in workspace, declaration


def test_the_details_are_a_sheet_that_scrolls_in_itself(narrow: str) -> None:
    """Positioned and a size container, so hidden text and the suggestion
    window stay inside it (docs 89 and 90)."""
    sheet = _rule(narrow, ".inspector")
    for declaration in (
        "position: absolute",
        "bottom: 0",
        "overflow-y: auto",
        "overscroll-behavior: contain",
        "container-type: size",
    ):
        assert declaration in sheet, declaration
    assert re.search(SHEET_HEIGHT, sheet), "the sheet's height is not its snap, or a drag's"


def test_the_plan_follows_the_sheet_at_rest_and_not_a_drag(narrow: str) -> None:
    """One refit of the plan per height, not one per frame of a drag."""
    plan = _rule(narrow, ".workspace__plan")
    assert "position: absolute" in plan
    assert re.search(r"bottom:\s*calc\(var\(--sheet-at\)\s*\*\s*100%\)", plan)
    assert "--sheet-drag" not in plan


def test_the_three_heights_are_the_ones_the_code_snaps_to(narrow: str) -> None:
    source = SHEET.read_text(encoding="utf-8")
    listing = source.split("export const SNAP_FRACTION", 1)[1].split("}", 1)[0]
    fractions = dict(re.findall(r"(peek|half|full): ([\d.]+)", listing))
    assert fractions == {"peek": "0.25", "half": "0.6", "full": "0.9"}
    assert re.search(r"--sheet-at:\s*0\.25", _rule(narrow, ".workspace"))
    for snap in ("half", "full"):
        rule = _rule(narrow, f".workspace[data-sheet='{snap}']")
        assert re.search(rf"--sheet-at:\s*{re.escape(fractions[snap])}\s*;", rule), snap


def test_the_tools_are_a_bar_at_the_foot_whose_names_open_upward(narrow: str) -> None:
    rail = _rule(narrow, ".tool-rail")
    for declaration in ("position: fixed", "bottom: 0", "height: var(--bar)"):
        assert declaration in rail, declaration
    app = _rule(narrow, ".app--workspace")
    assert "padding-bottom: var(--bar)" in app, "the bar would cover the year"
    assert re.search(LABEL_UPWARD, narrow), "the tools' names still open downward"


def test_the_menu_button_is_only_there_for_a_narrow_garden(css: str, narrow: str) -> None:
    """The front door and the wide workspace keep their header as it was."""
    assert "display: none" in _rule(css, ".site-header__menu")
    assert "display: contents" in _rule(css, ".site-header__more")
    assert "display: none" not in _rule(narrow, ".app--workspace .site-header__menu")


def test_text_fields_are_large_enough_that_ios_does_not_zoom(narrow: str) -> None:
    """Doc 87 left this to feature 5: iOS zooms into a field under 16 px."""
    fields = _rule(narrow, "input:not([type='checkbox']):not([type='radio']), select, textarea")
    assert re.search(r"font-size:\s*max\(1rem,\s*16px\)", fields)


def test_the_toast_drops_from_the_top_where_nothing_covers_it(narrow: str) -> None:
    toast = _rule(narrow, ".status-toast")
    assert "top:" in toast and "bottom: auto" in toast
