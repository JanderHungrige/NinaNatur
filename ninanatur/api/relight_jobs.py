"""A relight that may take minutes, off the request that asked for it.

The first "Sonne & Schatten" at a place reads the ground, the building model
and the laser before the light (`garden.relight`). On the preview that took
longer than the 90 s its proxy waits: the page got a 504 and showed nothing,
while the server went on and stored a map nobody was waiting for — and a
second press started it all again (the owner, 2026-09-28). Wave 26 reads every
stored laser window once more for the crown bases (doc 121), so every garden
met it once.

So a relight runs in a thread of its own, holding one of the heavy slots
(`ratelimit`) until it ends, and the request waits for it only `WAIT_S`: done
by then, it answers with the map as before; not, it answers 202 and the page
asks `status` until it is. One job per garden — a second press while one runs
waits for the same job, and takes no second slot.

An in-memory database — every API test's — has no file for a second thread to
open, and is relit in the request, as before. One process serves the app, so
the jobs are this module's to keep.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as NotYet
from contextlib import contextmanager
from dataclasses import dataclass, field

from ninanatur.api.ratelimit import HEAVY_SLOTS, heavy_now
from ninanatur.garden.light_worker import database_file
from ninanatur.ingest.db import connect

log = logging.getLogger(__name__)

#: How long a request waits for its relight: well inside the proxy's 90 s,
#: and longer than a relight whose ground, buildings and laser are stored.
WAIT_S = 20.0

Relight = Callable[[sqlite3.Connection, int], None]


@dataclass
class Slot:
    """A heavy slot taken for a relight, given back exactly once."""

    release: Callable[[], None]
    handed: bool = False
    _done: bool = field(default=False, repr=False)

    def give_back(self) -> None:
        if not self._done:
            self._done = True
            self.release()


@dataclass
class Job:
    future: Future[None]
    #: Whether it ended in an error, once it has ended.
    failed: bool = False


_lock = threading.Lock()
_jobs: dict[int, Job] = {}
_pool = ThreadPoolExecutor(max_workers=HEAVY_SLOTS, thread_name_prefix="relight")


@contextmanager
def slot() -> Iterator[Slot]:
    """A heavy slot, or the 429 `ratelimit.heavy` answers when none is free.
    Given back on the way out unless a job took it over."""
    taken = Slot(release=heavy_now())
    try:
        yield taken
    finally:
        if not taken.handed:
            taken.give_back()


def running(garden_id: int) -> Job | None:
    """The job relighting this garden now, if there is one."""
    with _lock:
        job = _jobs.get(garden_id)
    return job if job is not None and not job.future.done() else None


def start(conn: sqlite3.Connection, garden_id: int, taken: Slot, work: Relight) -> Job:
    """Relight this garden with the slot taken for it, which the job gives back
    — or the job already relighting it, leaving the slot to be given back.

    In a thread with a connection of its own; in this one where the database
    has no file (tests), and the job is then done when this returns. What was
    written on this connection is committed first, or the thread would not
    see it."""
    path = database_file(conn)
    if path is None:
        taken.handed = True
        future: Future[None] = Future()
        try:
            work(conn, garden_id)
            future.set_result(None)
        except Exception as error:  # noqa: BLE001 - held by the future, raised by `wait`
            future.set_exception(error)
        finally:
            taken.give_back()
        job = Job(future=future, failed=future.exception() is not None)
        with _lock:
            _jobs[garden_id] = job
        return job
    conn.commit()
    with _lock:
        current = _jobs.get(garden_id)
        if current is not None and not current.future.done():
            return current
        taken.handed = True
        job = Job(future=_pool.submit(_in_thread, path, garden_id, taken, work))
        _jobs[garden_id] = job
    job.future.add_done_callback(lambda done: _ended(job, done))
    return job


def wait(job: Job, seconds: float) -> bool:
    """Whether the job ended within `seconds`. An error it ended in is raised,
    as the request raised it before a relight left it."""
    try:
        job.future.result(timeout=seconds)
    except NotYet:
        return False
    return True


def status(garden_id: int) -> tuple[bool, bool, bool]:
    """(running, failed, known) for the garden's latest relight — known false
    where this process holds none: a restart, a deployment among them, loses
    a job, and the page must not take that for one that ended well."""
    with _lock:
        job = _jobs.get(garden_id)
    if job is None:
        return False, False, False
    return not job.future.done(), job.failed, True


def _in_thread(path: str, garden_id: int, taken: Slot, work: Relight) -> None:
    conn = connect(path, same_thread=False)
    try:
        work(conn, garden_id)
    except Exception:
        log.exception("relighting garden %d failed", garden_id)
        raise
    finally:
        conn.close()
        taken.give_back()


def _ended(job: Job, done: Future[None]) -> None:
    job.failed = done.exception() is not None


__all__ = ["WAIT_S", "Job", "Slot", "running", "slot", "start", "status", "wait"]
