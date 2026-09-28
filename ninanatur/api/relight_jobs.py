"""A relight that may take minutes, off the request that asked for it.

The first "Sonne & Schatten" at a place reads the ground, the building model
and the laser before the light (`garden.relight`). On the preview that took
longer than the 90 s its proxy waits: the page got a 504 and showed nothing,
while the server went on and stored a map nobody was waiting for — and a
second press started it all again (the owner, 2026-09-28). Wave 26 reads every
stored laser window once more for the crown bases (doc 121), so every garden
met it once.

So a relight runs in a thread of its own, holding one of the heavy slots
(`ratelimit`) until it ends, and the request that started it waits for it
only `WAIT_S`: done by then, it answers with the map as before; not, it
answers 202 and the page asks `status` until it is. A press while a job runs
answers 202 at once: it waited for the job at first, holding a server thread
for twenty seconds with no slot and no count, and forty such presses stalled
every page while the health check stayed green (review of c2ec593).

Jobs are kept by share token, not by garden id: SQLite gives a deleted
garden's id to the next one, and a new garden once joined the job of the one
deleted before it. An in-memory database — every API test's — has no file
for a second thread to open, and is relit in the request, as before. One
process serves the app, so the jobs are this module's to keep.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import wait as waited
from contextlib import contextmanager
from dataclasses import dataclass, field

from ninanatur.api.ratelimit import HEAVY_SLOTS, heavy_now
from ninanatur.garden.light_worker import database_file
from ninanatur.ingest.db import connect

log = logging.getLogger(__name__)

#: How long a request waits for the relight it started: well inside the
#: proxy's 90 s, and longer than a relight whose ground, buildings and laser
#: are stored.
WAIT_S = 20.0

Relight = Callable[[sqlite3.Connection, int], None]


class RelightFailed(Exception):
    """A relight ended in an error — logged, with its traceback, where it did.
    What the job keeps is this, not the error: a kept error holds its frames
    for as long as the process runs."""


class RelightAbandoned(Exception):
    """A relight claimed and never started: the press was turned away."""


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
    future: Future[None] = field(default_factory=Future)


_lock = threading.Lock()
_jobs: dict[str, Job] = {}
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


def claim(token: str) -> Job | None:
    """This garden, for a new relight — or None where one is running, which a
    press joins by asking its status. Decided under the lock, so two presses
    at once start one job."""
    with _lock:
        current = _jobs.get(token)
        if current is not None and not current.future.done():
            return None
        job = Job()
        _jobs[token] = job
        return job


def abandon(token: str, job: Job) -> None:
    """A claim the press never started — turned away for the house or the
    visitor's allowance. A press that joined it hears it ended."""
    with _lock:
        if _jobs.get(token) is job:
            del _jobs[token]
    if not job.future.done():
        job.future.set_exception(RelightAbandoned())


def start(conn: sqlite3.Connection, job: Job, garden_id: int, taken: Slot, work: Relight) -> None:
    """Run a claimed job with the slot taken for it, which the job gives back.

    In a thread with a connection of its own; in this one where the database
    has no file (tests), and the job is then done when this returns. What was
    written on this connection is committed first, or the thread would not
    see it. The slot is the job's only once the thread has it."""
    path = database_file(conn)
    if path is None:
        taken.handed = True
        _finish(job, taken, lambda: work(conn, garden_id), garden_id)
        return
    conn.commit()
    _pool.submit(_in_thread, path, job, garden_id, taken, work)
    taken.handed = True


def wait(job: Job, seconds: float) -> bool:
    """Whether the job ended within `seconds`. An error it ended in is raised,
    as the request raised it before a relight left it."""
    waited([job.future], timeout=seconds)
    if not job.future.done():
        return False
    job.future.result()
    return True


def status(token: str) -> tuple[bool, bool, bool]:
    """(running, failed, known) for the garden's latest relight — known false
    where this process holds none: a restart, a deployment among them, loses
    a job, and the page must not take that for one that ended well. Read off
    the job itself, never a flag a callback sets later."""
    with _lock:
        job = _jobs.get(token)
    if job is None:
        return False, False, False
    done = job.future.done()
    return not done, done and job.future.exception() is not None, True


def _in_thread(path: str, job: Job, garden_id: int, taken: Slot, work: Relight) -> None:
    def relit() -> None:
        conn = connect(path, same_thread=False)
        try:
            work(conn, garden_id)
        finally:
            conn.close()

    _finish(job, taken, relit, garden_id)


def _finish(job: Job, taken: Slot, run: Callable[[], None], garden_id: int) -> None:
    """Run the relight, give its slot back whatever happens — a connection
    that will not open included — and only then say how it ended."""
    failed = False
    try:
        run()
    except Exception:
        log.exception("relighting garden %d failed", garden_id)
        failed = True
    finally:
        taken.give_back()
    if failed:
        job.future.set_exception(RelightFailed(f"relighting garden {garden_id} failed"))
    else:
        job.future.set_result(None)


__all__ = ["WAIT_S", "Job", "RelightAbandoned", "RelightFailed", "Slot", "abandon", "claim",
           "slot", "start", "status", "wait"]
