"""The browser's own focus ring on the plan's shapes — the owner, 2026-09-28.

An `outline` on an SVG shape is drawn round its bounding box, in the canvas's
units, which are metres: the ring came out a wide band round every clicked
house. It was turned off for `:focus-visible` (Wave 7), which is when Chrome
draws it; Safari draws its own on every `:focus`, a click included, and the
band came back. The keyboard's ring is the shape's own stroke, and stays.
"""
import re
from pathlib import Path

STYLESHEET = Path("frontend/src/styles.css")


def _rules() -> list[tuple[str, str]]:
    text = re.sub(r"/\*.*?\*/", "", STYLESHEET.read_text(encoding="utf-8"), flags=re.S)
    return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", text)]


def test_every_focus_of_a_plan_shape_draws_no_outline() -> None:
    plain = [selector for selector, body in _rules()
             if re.search(r":focus(?!-)", selector) and "outline: none" in body]
    for shape in (".bed", ".obstacle", ".cluster"):
        assert any(shape in selector for selector in plain), (
            f"{shape}: nothing turns the browser's ring off on :focus")


def test_the_keyboard_keeps_a_ring_that_follows_the_shape() -> None:
    kept = [body for selector, body in _rules()
            if ".bed" in selector and ":focus-visible" in selector and "stroke:" in body]
    assert kept and all("non-scaling-stroke" in body for body in kept)
