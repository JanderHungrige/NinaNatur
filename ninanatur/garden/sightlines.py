"""What is visible from where somebody stands.

The same geometry the sun uses, from a different origin: a ray from an eye
rather than from the sun, and an obstacle blocks when its top rises above that
ray where it passes.

The value is not the novelty. "Will I actually see this plant" is the question
that decides where things go, and it is currently a guess.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ninanatur.garden.footprint import covers

# Standing eye height. A number, not a measurement — it is offered as a default
# and the viewpoint carries its own.
EYE_HEIGHT_M = 1.6


@dataclass(frozen=True)
class Viewpoint:
    x: float
    y: float
    eye_height_m: float = EYE_HEIGHT_M


@dataclass(frozen=True)
class Blocker:
    """Anything between the eye and the target.

    The same footprint the shading model uses, so a hedge blocks sight exactly
    as it blocks sun. Before Wave 10 both sides carried their own cylinder test
    and agreed only because both assumed a cylinder — the kind of agreement that
    holds until the day it silently stops.
    """

    id: int
    footprint: list[tuple[float, float]]
    height_m: float
    # Wave 8 heights are mostly assumed. An answer resting on one is marked, for
    # the same reason a filter reports what it dropped.
    estimated: bool = False


@dataclass(frozen=True)
class Target:
    x: float
    y: float
    #: Height of the ground the target stands on — a raised bed is not at zero.
    base_m: float
    height_m: float


@dataclass(frozen=True)
class Visibility:
    visible: bool
    #: Height above the target's own base at which it clears everything in the
    #: way. More useful than a yes/no: "sichtbar ab 1,2 m" says which plants
    #: belong there.
    visible_from_m: float
    hidden_by: int | None
    estimated: bool


def _blocks(eye: Viewpoint, target: Target, blocker: Blocker) -> float | None:
    """The height the sightline must clear because of this blocker, or None.

    A sightline is a shadow cast from an eye: the same swept-footprint geometry,
    with the eye where the sun would be. So the question is whether the target
    stands inside the blocker's shadow *as seen from the eye* — and that is one
    implementation, not two.

    None when the blocker is beside the line, behind the target, or around the
    viewer: you are under the tree, not behind it.
    """
    dx, dy = target.x - eye.x, target.y - eye.y
    span = math.hypot(dx, dy)
    if span <= 1e-9:
        return None
    if covers(blocker.footprint, (eye.x, eye.y)):
        return None  # standing inside it

    ux, uy = dx / span, dy / span
    # Nearest point of the footprint along the line of sight, and how far off it
    # the line passes.
    nearest: float | None = None
    for px, py in blocker.footprint:
        along = (px - eye.x) * ux + (py - eye.y) * uy
        across = abs((px - eye.x) * -uy + (py - eye.y) * ux)
        if along <= 0 or along >= span:
            continue
        if across > _HALF_WIDTH_TOLERANCE_M and not covers(
            blocker.footprint, (eye.x + ux * along, eye.y + uy * along)
        ):
            continue
        nearest = along if nearest is None else min(nearest, along)

    if nearest is None:
        # The corners may all fall outside while the line still crosses the
        # shape — check the midpoint of the segment that lies within it.
        midpoint = (eye.x + ux * span / 2, eye.y + uy * span / 2)
        if not covers(blocker.footprint, midpoint):
            return None
        nearest = span / 2

    rise = blocker.height_m - eye.eye_height_m
    return eye.eye_height_m + rise * (span / nearest)


#: A line of sight is a line, and a footprint corner exactly on it is a corner
#: the viewer sees past. This keeps that from depending on floating point noise.
_HALF_WIDTH_TOLERANCE_M = 1e-6


def visibility(eye: Viewpoint, target: Target, blockers: list[Blocker]) -> Visibility:
    """What can be seen of the target from the viewpoint."""
    needed = 0.0
    tallest: Blocker | None = None
    estimated = False

    for blocker in blockers:
        clear = _blocks(eye, target, blocker)
        if clear is None or clear <= needed:
            continue
        needed = clear
        tallest = blocker
        # Only blockers that actually block: an estimated height nowhere near
        # the line of sight must not make a certain answer look uncertain.
        estimated = blocker.estimated

    top = target.base_m + target.height_m
    visible_from = max(0.0, needed - target.base_m)
    return Visibility(
        visible=top > needed,
        visible_from_m=round(visible_from, 2),
        hidden_by=None if top > needed or tallest is None else tallest.id,
        estimated=estimated and top <= needed,
    )
