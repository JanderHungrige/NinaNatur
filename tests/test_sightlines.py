"""What you can actually see from where you stand.

The same geometry the sun uses, from a different origin: eye height instead of
solar altitude. Wave 7's height above ground per bed exists for this, and Wave
8's height provenance travels into it — a sightline computed from an estimated
building height must not be drawn as though it were surveyed.
"""
import pytest

from ninanatur.garden.footprint import Shape, footprint_of
from ninanatur.garden.sightlines import (
    EYE_HEIGHT_M,
    Blocker,
    Target,
    Viewpoint,
    visibility,
)

EYE = Viewpoint(x=0.0, y=0.0, eye_height_m=EYE_HEIGHT_M)


def _circle(x: float, y: float, radius: float) -> list[tuple[float, float]]:
    """The same footprint helper the shading model uses — one geometry, so a
    hedge blocks sight exactly as it blocks sun."""
    return footprint_of(shape=Shape.CIRCLE, x=x, y=y, width=radius * 2,
                        depth=None, rotation=0.0, points=None)


def _blocker(y: float, height: float, radius: float = 1.0, **kw: object) -> Blocker:
    return Blocker(id=1, footprint=_circle(0.0, y, radius), height_m=height, **kw)  # type: ignore[arg-type]


def test_nothing_in_the_way_is_fully_visible() -> None:
    seen = visibility(EYE, Target(x=0.0, y=10.0, base_m=0.0, height_m=0.5), [])
    assert seen.visible is True
    assert seen.visible_from_m == 0.0
    assert seen.hidden_by is None


def test_a_hedge_hides_a_ground_cover_behind_it() -> None:
    # The question the whole feature answers: will I actually see this plant.
    seen = visibility(
        EYE,
        Target(x=0.0, y=10.0, base_m=0.0, height_m=0.2),
        [_blocker(y=5.0, height=2.0)],
    )
    assert seen.visible is False
    assert seen.hidden_by == 1


def test_the_same_hedge_does_not_hide_a_tall_perennial() -> None:
    # 3 m, not 2.5: since Wave 10 the binding point is the hedge's *near* edge
    # rather than its centre, which is what you actually look over, so a 2 m
    # hedge one metre deep at 5 m needs 2.6 m at 10 m rather than 2.4.
    seen = visibility(
        EYE,
        Target(x=0.0, y=10.0, base_m=0.0, height_m=3.0),
        [_blocker(y=5.0, height=2.0)],
    )
    assert seen.visible is True


def test_it_says_from_what_height_the_plant_becomes_visible() -> None:
    """More useful than a yes/no: "sichtbar ab 1,2 m" tells the user which
    plants belong there."""
    seen = visibility(
        EYE,
        Target(x=0.0, y=10.0, base_m=0.0, height_m=3.0),
        [_blocker(y=5.0, height=2.0)],
    )
    # Eye at 1.6 m; the blocker's near edge is at 4 m, not its centre at 5 m,
    # because that is the edge you look over. 1.6 + (2 − 1.6) × (10 / 4) = 2.6.
    assert seen.visible_from_m == pytest.approx(2.6, abs=0.05)


def test_a_raised_bed_in_front_is_not_hidden() -> None:
    # Wave 7 stored height_above_ground for exactly this.
    # 1.4 m rather than 1.0: looking *down* over a low blocker, the near-edge
    # rule leaves a 1 m wall barely blocking anything at all.
    hidden = visibility(
        EYE, Target(x=0.0, y=10.0, base_m=0.0, height_m=0.3), [_blocker(y=5.0, height=1.4)]
    )
    raised = visibility(
        EYE, Target(x=0.0, y=10.0, base_m=1.2, height_m=0.3), [_blocker(y=5.0, height=1.4)]
    )
    assert hidden.visible is False
    assert raised.visible is True


def test_something_behind_the_target_never_blocks_it() -> None:
    seen = visibility(
        EYE,
        Target(x=0.0, y=5.0, base_m=0.0, height_m=0.3),
        [_blocker(y=10.0, height=8.0)],
    )
    assert seen.visible is True


def test_something_beside_the_line_of_sight_does_not_block() -> None:
    beside = Blocker(id=2, footprint=_circle(8.0, 5.0, 1.0), height_m=5.0)
    seen = visibility(EYE, Target(x=0.0, y=10.0, base_m=0.0, height_m=0.3), [beside])
    assert seen.visible is True


def test_standing_inside_a_blocker_is_not_blocked_by_it() -> None:
    # You are under the tree, not behind it.
    around = Blocker(id=3, footprint=_circle(0.0, 0.0, 3.0), height_m=8.0)
    seen = visibility(EYE, Target(x=0.0, y=10.0, base_m=0.0, height_m=0.3), [around])
    assert seen.visible is True


def test_the_tallest_blocker_is_the_one_named() -> None:
    seen = visibility(
        EYE,
        Target(x=0.0, y=12.0, base_m=0.0, height_m=0.2),
        [
            _blocker(y=4.0, height=1.5),
            Blocker(id=9, footprint=_circle(0.0, 8.0, 1.0), height_m=4.0),
        ],
    )
    assert seen.hidden_by == 9


def test_an_estimated_height_makes_the_answer_estimated() -> None:
    """A sightline computed from a guessed building height must not be drawn as
    though it were surveyed."""
    guessed = Blocker(id=4, footprint=_circle(0.0, 5.0, 1.0), height_m=7.0, estimated=True)
    seen = visibility(EYE, Target(x=0.0, y=10.0, base_m=0.0, height_m=0.3), [guessed])
    assert seen.visible is False
    assert seen.estimated is True


def test_a_measured_blocker_gives_a_certain_answer() -> None:
    known = Blocker(id=5, footprint=_circle(0.0, 5.0, 1.0), height_m=7.0, estimated=False)
    seen = visibility(EYE, Target(x=0.0, y=10.0, base_m=0.0, height_m=0.3), [known])
    assert seen.estimated is False


def test_only_blockers_that_actually_block_affect_confidence() -> None:
    # An estimated height that is nowhere near the line of sight must not make
    # a perfectly certain answer look uncertain.
    far = Blocker(id=6, footprint=_circle(20.0, 5.0, 1.0), height_m=9.0, estimated=True)
    seen = visibility(EYE, Target(x=0.0, y=10.0, base_m=0.0, height_m=0.3), [far])
    assert seen.visible is True
    assert seen.estimated is False


def test_a_target_at_the_viewpoint_is_visible() -> None:
    # Degenerate, and a division by zero if unguarded.
    seen = visibility(EYE, Target(x=0.0, y=0.0, base_m=0.0, height_m=0.3), [])
    assert seen.visible is True
