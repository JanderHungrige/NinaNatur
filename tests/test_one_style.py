"""One panel, one style (doc 92): the stylesheet's scales, one look for a box
and one for what sits inside it.

Measured before, on the preview (V0.20.177), from computed styles: the garden
in the details drew three kinds of boxed panel with text in seven sizes, a bed
two kinds with text in eight. The stylesheet declared the panel's box again,
whole, in nine other rules and a line with an 8px radius in seven; it held 57
distinct paddings and 23 font sizes, and no custom property named either.
"""
import re
from pathlib import Path

import pytest

STYLESHEET = Path("frontend/src/styles.css")
SCALES = {
    "--space-1": "0.25rem", "--space-2": "0.5rem", "--space-3": "0.75rem",
    "--space-4": "1rem", "--space-5": "1.25rem", "--space-6": "1.5rem",
    "--text-xs": "0.78rem", "--text-sm": "0.85rem", "--text-md": "0.95rem",
    "--text-base": "1rem", "--text-lg": "1.15rem",
    "--radius": "12px", "--radius-sm": "8px",
}
# The panels, including the ones under another name.
PANELS = (
    ".panel", ".soil-line", ".first-steps__step", ".site-header .garden-id__body",
    ".app--workspace .account-drawer", ".app--workspace .site-header__more",
)
# Every box drawn the way a panel is.
BOXES = PANELS + (".status-toast", ".canvas", ".sun-readout", ".shortcut-help")
# What sits inside a panel with a line round it.
ROWS = (
    ".change", ".bed-plantings__row", ".suggestion-window", ".bed-button", ".garden-id__token",
    "input:not([type='checkbox']):not([type='radio'])", "select", "textarea",
    ".tool-rail__tool:hover .tool-rail__label",
)
PANEL_LOOK = (
    "border: 1px solid var(--line)", "border-radius: var(--radius)", "background: var(--bg-raised)",
)
ROW_LOOK = ("border: 1px solid var(--line)", "border-radius: var(--radius-sm)")
SPACED = PANELS + (
    ".inspector", ".inspector__view", ".inspector .panel", ".hint", ".panel h2", ".panel h3",
)


@pytest.fixture(scope="module")
def css() -> str:
    text = STYLESHEET.read_text(encoding="utf-8")
    assert len(text) > 1000, f"{STYLESHEET} looks empty — the test would be vacuous"
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def _rules(css: str) -> list[tuple[list[str], str]]:
    """Every innermost rule, as its selectors and its body; media blocks unwrapped."""
    return [
        ([name.strip() for name in selectors.split(",") if name.strip()], body)
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
    ]


def _narrow(css: str) -> str:
    blocks = re.findall(r"^@media \(width < 66rem\) \{(.*?)^\}", css, re.S | re.M)
    assert len(blocks) == 1
    return blocks[0]


def test_the_scales_and_radii_are_custom_properties_on_root(css: str) -> None:
    root = re.search(r"^:root\s*\{([^{}]*)\}", css, re.M)
    assert root is not None, "no :root block, or a rule nested inside it"
    for name, value in SCALES.items():
        assert re.search(rf"{re.escape(name)}:\s*{re.escape(value)}\s*;", root.group(1)), name


def test_the_panel_look_is_declared_once_for_every_box(css: str) -> None:
    holding = [names for names, body in _rules(css) if all(part in body for part in PANEL_LOOK)]
    assert len(holding) == 1, f"the panel look is declared in {len(holding)} rules: {holding}"
    for box in BOXES:
        assert box in holding[0], f"{box} does not share the panel look"


def test_the_row_look_is_declared_once_for_everything_inside_a_panel(css: str) -> None:
    holding = [names for names, body in _rules(css) if all(part in body for part in ROW_LOOK)]
    assert len(holding) == 1, f"the row look is declared in {len(holding)} rules: {holding}"
    for row in ROWS:
        assert row in holding[0], f"{row} does not share the row look"


def test_no_radius_is_written_as_a_number_the_scale_names(css: str) -> None:
    assert not re.findall(r"border-radius:\s*(?:8|12)px", css)


def test_every_font_size_in_the_scales_range_is_one_of_its_steps(css: str) -> None:
    """0.7 to 1.25rem. The details' title, the landing's figures and headings, the
    score's number, the compass and a phone's 16 px floor for fields lie outside it."""
    inside = sorted({float(size) for size in re.findall(r"font-size:\s*([\d.]+)rem", css)
                     if 0.7 <= float(size) <= 1.25})
    assert inside == [], f"font sizes in the scale's range written as numbers: {inside}"


def test_the_panels_spacing_comes_from_the_scale(css: str) -> None:
    for names, body in _rules(css):
        if not any(name in SPACED for name in names):
            continue
        for prop, value in re.findall(r"\b(padding|gap|margin)[a-z-]*:\s*([^;]+);", body):
            assert not re.search(r"\d(?:\.\d+)?rem", value), f"{names}: {prop}: {value}"


def test_a_phones_plan_controls_take_the_smallest_steps(css: str) -> None:
    """Measured 9 px past their 341 px row on V0.20.177 (doc 91's known issue)."""
    narrow = _narrow(css)
    row = re.search(r"\.workspace \.canvas-controls__row\s*\{([^}]*)\}", narrow)
    button = re.search(r"\.workspace \.canvas-controls__row button\s*\{([^}]*)\}", narrow)
    assert row is not None and "gap: var(--space-1)" in row.group(1)
    assert button is not None and "font-size: var(--text-xs)" in button.group(1)
