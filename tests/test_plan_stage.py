"""The plan's size comes from the page, never from the plan (Wave 23, feature 0).

Read as text, like the sheet's other guards (see test_stylesheet.py for why
vitest cannot): jsdom lays nothing out, so the rule that broke — a drawing whose
height followed its own measurement — is visible only in the CSS.
"""
import re
from pathlib import Path

import pytest

STYLESHEET = Path("frontend/src/styles.css")
APP = Path("frontend/src/App.tsx")


@pytest.fixture(scope="module")
def css() -> str:
    text = STYLESHEET.read_text(encoding="utf-8")
    assert len(text) > 1000, f"{STYLESHEET} looks empty — the test would be vacuous"
    # Comments out first: a rule described in a comment is not a rule.
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def _rules(css: str, selector: str) -> list[str]:
    """The bodies of every top-level block whose selector is exactly `selector`."""
    return re.findall(rf"(?m)^{re.escape(selector)}\s*\{{([^}}]*)\}}", css)


def test_the_drawing_fills_its_stage_instead_of_sizing_it(css: str) -> None:
    """`height: auto` let the viewBox set the drawing's height, and the viewBox
    came from the drawing's measured height: one short measurement, and the plan
    stayed 12 px high until a reload."""
    body = " ".join(_rules(css, ".canvas"))
    assert "height: 100%" in body
    assert "height: auto" not in body
    assert "max-height" not in body, "capping the drawing is the stage's job now"


def test_the_stage_takes_its_height_from_the_window(css: str) -> None:
    body = " ".join(_rules(css, ".canvas-stage"))
    heights = re.findall(r"(?<![-\w])height:\s*([^;]+);", body)
    assert heights, ".canvas-stage declares no height of its own"
    assert all("vh" in h for h in heights), heights
    assert all("rem" in h for h in heights), f"no floor under the stage: {heights}"


def test_the_stage_can_size_by_its_own_width(css: str) -> None:
    """`75cqi` resolves against the nearest size container. Without one it falls
    back to the viewport, and the cap would quietly mean something else."""
    assert any("cqi" in body for body in _rules(css, ".canvas-stage"))
    assert any("container-type: inline-size" in body for body in _rules(css, ".canvas-wrap"))


def test_the_plan_column_stays_in_view_only_when_there_are_two(css: str) -> None:
    """Sticky in a single column would pin the plan over the forms around it."""
    one_column_below = re.search(r"@media \(max-width: ([\d.]+)rem\)\s*\{\s*\.layout", css)
    assert one_column_below is not None
    sticky = re.search(
        r"@media \(min-width: ([\d.]+)rem\)\s*\{\s*\.column--plan\s*\{([^}]*)\}", css
    )
    assert sticky is not None, "no sticky rule for the plan column"
    assert float(sticky.group(1)) > float(one_column_below.group(1))
    assert "position: sticky" in sticky.group(2)
    assert "overflow-y: auto" in sticky.group(2), "a column taller than the window hides its end"


def test_the_markup_names_the_plan_column() -> None:
    assert 'className="column column--plan"' in APP.read_text(encoding="utf-8")


def test_the_status_toast_floats_and_holds_still_for_reduced_motion(css: str) -> None:
    assert any("position: fixed" in body for body in _rules(css, ".status-toast"))
    start = css.index("@media (prefers-reduced-motion: reduce)")
    block = css[start : css.index("\n}", css.index("{", start))]
    assert ".status-toast" in block, "the toast still moves for someone who asked for less"
