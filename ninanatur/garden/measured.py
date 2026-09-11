"""Replacing a garden's assumed buildings with measured ones.

Every building around a garden arrives as a guess. Wave 17 stood those guesses
on measured ground; Wave 19's first two features found the measurements. This is
where they meet the garden — and the rule that governs it is the one thing worth
getting right.

**The person standing in the garden outranks the survey.** They can see the
house. The model saw it from an aeroplane, some years ago, through whatever was
growing over it. Where they disagree, the gardener is right — and their answer
has to survive the next refresh, which means it is recognised by its provenance
rather than by being the value that happens to be stored.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

from ninanatur.garden.models import Garden
from ninanatur.garden.objects import ROOFED
from ninanatur.garden.roofs import Roof
from ninanatur.geo.lod2 import Lod2Building
from ninanatur.geo.measure import height_of, looks_contaminated
from ninanatur.geo.surface import SurfaceWindow
from ninanatur.geo.surroundings import HeightSource

log = logging.getLogger(__name__)

#: How much of a drawn building a surveyed one must cover to be the same
#: building.
#:
#: **Overlap rather than distance between centres**, and the difference is not
#: academic. Measured against Cologne with a centre rule at eight metres: a
#: 47 m² terraced house was handed the 2.7 m pent roof of the garage beside it,
#: because the garage's centre was nearer than the tolerance and nothing else
#: was consulted. A garage does not overlap a house.
#:
#: A third rather than a half: OSM outlines and the official ground plans agree
#: closely but not exactly, and a terraced house whose OSM outline includes its
#: porch would fail a stricter rule.
MATCH_OVERLAP = 0.34

#: How finely a footprint is sampled to measure that overlap. Half a metre —
#: fine enough that a garage cannot pass and coarse enough that a house is a
#: hundred points rather than ten thousand.
OVERLAP_STEP_M = 0.5

#: A surveyed height this far from the drawn one is a different building.
#:
#: Not a correction but a refusal. Matching by position alone will occasionally
#: pair a garage with the house behind it, and the tell is that the numbers are
#: nowhere near each other.
IMPLAUSIBLE_M = 15.0

#: The kinds measured here: the ones with a roof.
#:
#: Everything else a garden holds is ground — the outline, a lawn, a street — or
#: stands without being a building. A tree found by the canopy pass and accepted
#: is stored as `measured`, so this module used to measure it again on every
#: recompute: against the survey, where overhanging a house hands it that
#: house's roof, and against the laser surface as though its crown were one.
BUILDINGS = frozenset(kind.value for kind in ROOFED)

#: min x, min y, max x, max y.
Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class Measurement:
    """What was found for one drawn building, and where it came from."""

    obstacle_id: int
    height_m: float
    source: HeightSource
    roof: Roof | None = None
    eaves_m: float | None = None
    #: Something is standing over this roof that is not the roof. The height is
    #: still offered — the caller decides — but it is offered with a warning.
    suspect: bool = False


def measure(
    garden: Garden,
    surveyed: list[Lod2Building] | None = None,
    surface: SurfaceWindow | None = None,
) -> list[Measurement]:
    """What can be measured about this garden's buildings.

    Returns nothing for a building the user has spoken about: `height_source`
    of `user` is a decision, not a default, and re-measuring it would undo a
    correction somebody made on purpose. And nothing for what is not a
    building: see `BUILDINGS`.
    """
    boxed = _boxed(surveyed)
    found: list[Measurement] = []
    for obstacle in garden.obstacles:
        if obstacle.kind not in BUILDINGS:
            continue
        if obstacle.height_source == HeightSource.USER.value:
            continue
        if not obstacle.footprint or len(obstacle.footprint) < 3:
            continue
        from_survey = _from_survey(obstacle, boxed)
        from_raster = _from_surface(obstacle, surface)
        best = _reconcile(from_survey, from_raster)
        if best is not None:
            found.append(best)
    return found


def _reconcile(
    survey: Measurement | None, raster: Measurement | None
) -> Measurement | None:
    """Two independent measurements of one building, and what to do when they
    disagree.

    The survey wins where both exist and agree, because it measured this
    building against its own ground plan. Where they disagree by more than
    `IMPLAUSIBLE_M` the *match* is what is suspect — position alone will
    occasionally pair a garage with the house behind it, and the tell is that
    the two numbers are nowhere near each other. Then the raster wins, because
    it was measured over the footprint actually drawn on this plan.

    Having two sources is what makes this checkable at all. With one, a
    mismatched building would simply be wrong.
    """
    if survey is None:
        return raster
    if raster is None:
        return survey
    if abs(survey.height_m - raster.height_m) > IMPLAUSIBLE_M:
        log.info(
            "survey and raster disagree on obstacle %s (%.1f m vs %.1f m) —"
            " taking the raster, the match is probably the wrong building",
            survey.obstacle_id, survey.height_m, raster.height_m,
        )
        return raster
    return survey


def _from_survey(
    obstacle: object, boxed: list[tuple[Lod2Building, Box]]
) -> Measurement | None:
    """The official 3D model, matched by position.

    Candidates arrive already on the garden's axes — see `lod2.in_garden_frame`
    — so this is a subtraction rather than a projection.

    Preferred over our own raster measurement wherever it exists: the survey
    measured this building against its own ground plan and states its accuracy,
    where the raster route is a percentile over an outline somebody drew in OSM.
    """
    if not boxed:
        return None
    drawn = [(float(p[0]), float(p[1])) for p in getattr(obstacle, "footprint", [])]
    points = _sample(drawn)
    if not points:
        return None
    reach = _box(points)
    best = None
    best_share = MATCH_OVERLAP
    for candidate, box in boxed:
        # A sample can only be inside an outline whose box holds it, so a
        # building whose box misses every sample cannot match. One box test
        # instead of a polygon test per sample, and a tile holds 2,601 of them.
        if not _overlaps(box, reach):
            continue
        share = _covered(points, candidate.outline)
        if share > best_share:
            best, best_share = candidate, share
    nearest = best
    if nearest is None:
        return None
    return Measurement(
        obstacle_id=int(getattr(obstacle, "obstacle_id", 0)),
        height_m=round(nearest.height_m, 1),
        source=HeightSource.SURVEYED,
        roof=nearest.roof,
        eaves_m=nearest.eaves_m,
    )


def _from_surface(obstacle: object, surface: SurfaceWindow | None) -> Measurement | None:
    """Our own measurement, from the laser surface over the drawn footprint."""
    if surface is None:
        return None
    footprint = [(float(p[0]), float(p[1])) for p in getattr(obstacle, "footprint", [])]
    height = height_of(surface, footprint)
    if height is None:
        return None
    return Measurement(
        obstacle_id=int(getattr(obstacle, "obstacle_id", 0)),
        height_m=height,
        source=HeightSource.MEASURED,
        suspect=looks_contaminated(surface, footprint),
    )


def apply(conn: sqlite3.Connection, found: list[Measurement]) -> int:
    """Write the measurements. Returns how many buildings changed.

    A suspect measurement is not written. Something is standing over that roof
    and the honest response is to keep the assumption rather than to publish a
    number that is probably a tree — the warning belongs in the log, where
    somebody looking for why a garden is dark will find it.
    """
    changed = 0
    for measurement in found:
        if measurement.suspect:
            log.info(
                "not measuring obstacle %s: something stands over it",
                measurement.obstacle_id,
            )
            continue
        if measurement.roof is None:
            conn.execute(
                "UPDATE element SET height = ?, height_source = ?"
                " WHERE element_id = ? AND height_source != ?",
                (measurement.height_m, measurement.source.value,
                 measurement.obstacle_id, HeightSource.USER.value),
            )
        else:
            conn.execute(
                "UPDATE element SET height = ?, height_source = ?, roof = ?,"
                " roof_source = ?, eaves_m = COALESCE(?, eaves_m)"
                " WHERE element_id = ? AND height_source != ?",
                (measurement.height_m, measurement.source.value,
                 measurement.roof.value, measurement.source.value,
                 measurement.eaves_m, measurement.obstacle_id,
                 HeightSource.USER.value),
            )
        changed += 1
    conn.commit()
    return changed


def _boxed(surveyed: list[Lod2Building] | None) -> list[tuple[Lod2Building, Box]]:
    """Each surveyed building with the box around it — worked out once per
    garden rather than once per building drawn on it."""
    return [(b, _box(b.outline)) for b in surveyed or [] if len(b.outline) >= 3]


def _box(points: list[tuple[float, float]]) -> Box:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _overlaps(a: Box, b: Box) -> bool:
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def _sample(footprint: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Points spread over a footprint, for measuring how much of it is covered."""
    if len(footprint) < 3:
        return []
    xs = [p[0] for p in footprint]
    ys = [p[1] for p in footprint]
    points: list[tuple[float, float]] = []
    y = min(ys)
    while y <= max(ys):
        x = min(xs)
        while x <= max(xs):
            if _inside(footprint, x, y):
                points.append((x, y))
            x += OVERLAP_STEP_M
        y += OVERLAP_STEP_M
    return points


def _covered(points: list[tuple[float, float]], outline: list[tuple[float, float]]) -> float:
    """What share of those points falls inside this outline."""
    if not points or len(outline) < 3:
        return 0.0
    return sum(1 for x, y in points if _inside(outline, x, y)) / len(points)


def _inside(polygon: list[tuple[float, float]], x: float, y: float) -> bool:
    inside = False
    n = len(polygon)
    for i in range(n):
        ax, ay = polygon[i]
        bx, by = polygon[(i + 1) % n]
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
    return inside


__all__ = [
    "BUILDINGS",
    "IMPLAUSIBLE_M",
    "MATCH_OVERLAP",
    "Measurement",
    "apply",
    "measure",
]
