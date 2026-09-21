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
# A theme's own sheet (doc 97) declares the plan's hooks — `--plan-*`, used in
# the main sheet with Technisch's look as the fallback — and uses the palette.
THEME_SHEETS = sorted(Path("frontend/src/themes").glob("**/*.css"))

# Custom properties set from TypeScript rather than declared in the sheet.
# `--sheet-drag` is a finger's height while it drags the sheet (doc 91): declared
# in the sheet, it would stop the sheet falling back to its resting height.
SET_INLINE = frozenset({"--fill", "--sheet-drag"})

# Not a colour, so it needs no dark-mode counterpart: sizes, and the scales of
# space and type (doc 92).
NOT_A_COLOUR = frozenset({
    "--radius", "--radius-sm", "--bar", "--sheet-at",
    "--space-1", "--space-2", "--space-3", "--space-4", "--space-5", "--space-6",
    "--text-xs", "--text-sm", "--text-md", "--text-base", "--text-lg",
})


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
    themes = [sheet.read_text(encoding="utf-8") for sheet in THEME_SHEETS]
    hooks = {name for sheet in themes for name in _declared(sheet) if name.startswith("--plan-")}
    used = _used(css).union(*(_used(sheet) for sheet in themes))
    unknown = sorted(used - _declared(css) - SET_INLINE - hooks)
    assert unknown == [], f"used but never declared: {unknown}"


def test_a_theme_sheet_is_found(css: str) -> None:
    """Guards the hooks above: with no theme sheet read, every hook would fail."""
    assert any(sheet.parent.name == "draft-sketch" for sheet in THEME_SHEETS)


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


# The breakpoint guard for the two columns moved to tests/test_workspace_layout.py
# with the workspace that replaced them (Wave 23, doc 87): the plan must still
# never get narrower when the window gets wider.


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


def test_the_film_covers_the_window_it_is_in() -> None:
    """A 16:9 clip and a window of any shape at all. `contain` would letterbox
    it — a photograph in a frame rather than the page's ground — and no
    object-fit at all stretches the meadow."""
    css = STYLESHEET.read_text(encoding="utf-8")
    start = css.index(".living__video")
    block = css[start : css.index("}", start)]
    assert "object-fit: cover" in block
    # Anchored low: a portrait phone crops the width, and the flowers are in the
    # lower half of the frame while the top is blurred hedge.
    assert "object-position" in block


def test_the_video_credit_is_quiet_but_readable() -> None:
    """The user asked for it small and light, and the first attempt took that
    literally: muted grey at 75% opacity measured 2.35 contrast against the
    meadow. Quiet is the font size's job — a credit nobody can read credits
    nobody."""
    css = STYLESHEET.read_text(encoding="utf-8")
    start = css.index(".landing__credit {")
    block = css[start : css.index("}", start)]
    assert "opacity" not in block, "faded twice: the colour already carries it"
    assert ".app--front-door .landing__credit" in css, "unreadable over the film"


def test_a_checkbox_is_not_stretched_across_the_panel() -> None:
    """`input { width: 100% }` is right for a text field and wrong for a tick
    box: it made the box 908 pixels wide and pushed its own label onto the next
    line. Reported as "the checkbox is not aligned with the text", which is what
    it looks like from outside — the box was simply the width of the panel.

    Asserted on the selector rather than on a rendered pixel, because the whole
    point is that the rule must never quietly take checkboxes back.
    """
    # Comments stripped first. Two earlier versions of this test passed while
    # the bug was present: one matched a `:focus-visible` rule two hundred lines
    # up, and one read the explanatory comment as the selector. A guard that
    # cannot fail guards nothing, so this one was checked by putting the bug
    # back and watching it go red.
    css = re.sub(r"/\*.*?\*/", "", STYLESHEET.read_text(encoding="utf-8"), flags=re.S)
    # *Any* selector that can reach an input, not only one that starts with it.
    # The third version of this test still missed `.map-picker input` and
    # `.landing__way input`, which are more specific than the base rule and were
    # the ones actually stretching the box on the page somebody reported.
    offenders = [
        block.rsplit("}", 1)[-1].strip().rstrip("{").strip()
        for block in css.split("width: 100%")[:-1]
        if re.search(r"(^|[\s,>])input(?![\w-])", block.rsplit("}", 1)[-1])
        and "checkbox" not in block.rsplit("}", 1)[-1]
    ]
    assert offenders == [], f"a full-width rule still catches tick boxes: {offenders}"


def test_the_map_takes_the_finger_rather_than_the_page(css: str) -> None:
    """Doc 31, B1: on the map a finger drags the map.

    Without `touch-action: none` the browser scrolls the page under the finger
    and the map never moves — which is what a phone did, since panning wanted
    the right mouse button. And the surface is the width it is given rather than
    a 640 px it is not: the projection measures this element, and a fixed width
    would lie to it.
    """
    rule = re.search(r"^\.map-picker__surface \{([^}]*)\}", css, re.M)
    assert rule is not None, "no .map-picker__surface rule"
    assert "touch-action: none" in rule.group(1), "a finger on the map scrolls the page"
    assert "width: 100%" in rule.group(1), "the surface's width is not the layout's to give"


def test_the_plans_hand_is_bundled_and_not_fetched() -> None:
    """Patrick Hand ships beside the app (doc 101). The policy is
    `font-src 'self'` (Wave 20), so a CDN would simply not load — and a plan
    lettered in the fallback is a plan in two hands."""
    sheets = [sheet.read_text(encoding="utf-8") for sheet in THEME_SHEETS]
    faces = [sheet for sheet in sheets if "@font-face" in sheet]
    assert faces, "no theme declares a font of its own"
    for sheet in faces:
        for url in re.findall(r"src:\s*url\(([^)]+)\)", sheet):
            assert not url.strip("'\"").startswith(("http://", "https://", "//")), url
            local = (Path("frontend/src/themes/draft-sketch") / url.strip("'\"")).resolve()
            assert local.is_file(), f"{local} is declared and not there"
            assert (local.parent / "OFL.txt").is_file(), "a bundled font ships its licence"


def test_the_hand_letters_the_drawing_and_nothing_else() -> None:
    """The plan's own text and its title block; never the interface, which is a
    control panel rather than a drawing (doc 101)."""
    sheet = Path("frontend/src/themes/draft-sketch/theme.css").read_text(encoding="utf-8")
    # Every rule that sets the hand, less the @font-face that declares it: the
    # selectors are what stands between the comment above and the brace.
    rules = [match.group(1) for match
             in re.finditer(r"([^{}/]*)\{\s*font-family:\s*'Patrick Hand'", sheet)
             if "@font-face" not in match.group(1)]
    assert len(rules) == 1, rules
    selectors = {part.strip() for part in rules[0].split(",") if part.strip()}
    assert selectors == {".plan-theme--draft-sketch text", ".plan-furniture--draft-sketch"}
    assert "'Patrick Hand'" not in STYLESHEET.read_text(encoding="utf-8")
