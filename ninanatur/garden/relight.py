"""Everything a relight reads before the light, and then the light.

The ground, the survey's building model and — in the seven states that publish
one — the laser, each read once for a place and stored, and only then the
light (docs 104, 107, 121). Where they are stored this is seconds. Where they
are not it is the longest wait in the app: the laser alone took 31 s on a
workstation and the chain over 90 s on the preview, whose proxy then cut the
request off (the owner, 2026-09-28). So `api.relight_jobs` runs it off the
request, and each run says in the log what took how long — the question that
had no answer from outside the server. Its first answer, in the image: *laser
385.4 s*, nearly all of it the roof test, which now takes half a second
(`geo.inside`, doc 107).
"""
from __future__ import annotations

import logging
import sqlite3
import time
from collections.abc import Callable
from typing import TypeVar

from ninanatur.garden.building_sync import measure_buildings
from ninanatur.garden.cloud_sync import ensure_cloud, fill_crown_bases
from ninanatur.garden.light_worker import recompute_light
from ninanatur.garden.store import load_garden
from ninanatur.garden.terrain_sync import ensure_terrain

log = logging.getLogger(__name__)

T = TypeVar("T")


def relight(conn: sqlite3.Connection, garden_id: int) -> None:
    """Read what the light rests on where it has not been read, then compute it.

    The order is the dependency: a raw surface model is only object heights
    once the terrain is off it, and the laser cannot tell a roof from a crown
    without the building model (doc 107); the crowns' bases come from the laser
    (doc 121), the light from all of it.
    """
    took: list[str] = []

    def timed(name: str, step: Callable[[], T]) -> T:
        start = time.perf_counter()
        result = step()
        took.append(f"{name} {time.perf_counter() - start:.1f} s")
        return result

    try:
        timed("terrain", lambda: ensure_terrain(conn, load_garden(conn, garden_id)))
        measured = timed("buildings",
                         lambda: measure_buildings(conn, load_garden(conn, garden_id)))
        timed("laser", lambda: ensure_cloud(conn, load_garden(conn, garden_id),
                                            buildings=measured.buildings))
        timed("crown bases", lambda: fill_crown_bases(conn, load_garden(conn, garden_id)))
        timed("light", lambda: recompute_light(conn, garden_id))
    finally:
        # A run that fails says the steps it got through too: which was slow
        # is the question, and a failure is where it is asked.
        log.info("relit garden %d: %s", garden_id, ", ".join(took) or "nothing")


__all__ = ["relight"]
