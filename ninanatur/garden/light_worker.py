"""The light, computed in a process of its own — Wave 20, feature 5, part 4.

Measured on the preview on 2026-09-11: a garden of 87 elements took 12.9 s to
relight alone, two at once took 37.8 s each, and a plain `GET` of a garden went
from 8 ms to a median of 220 ms and a worst of 1.05 s while they ran. The light
is pure Python arithmetic; in the serving process it holds the interpreter lock
every other request needs, so two relights starve each other and everybody
else. In a process of its own it holds nobody's lock but its own.

A pool of `NINANATUR_LIGHT_WORKERS` processes (default: one per slot the API
hands out), started with the app and warmed at startup so the first relight
does not pay for starting a process. Three ways a second process could go
wrong, and what is done about each:

- **A lock the request still holds.** The worker opens a connection of its own
  to the same file. A write the request had not committed would lock it out for
  the busy timeout and then fail — so the request commits first.
- **A database only this process can see.** An in-memory database — every API
  test's — has no file to open elsewhere, and is computed here, as before.
- **A worker that dies** — killed for memory, say — breaks the whole pool. The
  pool is replaced and the job run once more; relighting is idempotent.

`forkserver`, not the platform's `fork`: a fork of the serving process would
copy locks its other threads hold mid-request. A fork of a small, quiet server
process copies nothing but the imports, which are preloaded once.
"""
from __future__ import annotations

import logging
import multiprocessing
import os
import sqlite3
import threading
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from multiprocessing.context import BaseContext
from typing import TypeVar

from ninanatur.garden import lighting, lightview
from ninanatur.garden.lightgrid import LightGrid
from ninanatur.garden.models import Garden
from ninanatur.ingest.db import connect

log = logging.getLogger(__name__)

WORKERS_ENV = "NINANATUR_LIGHT_WORKERS"
#: One per slot `api.ratelimit` hands out, so a relight holding a slot never
#: queues for a process. Kept equal by a test rather than by an import: the
#: garden layer does not reach up into the API's.
DEFAULT_WORKERS = 2
#: A worker is replaced after this many jobs, giving back whatever a long-lived
#: process accumulates.
JOBS_PER_WORKER = 200
#: Starting the server process and importing the model, once.
WARM_TIMEOUT_S = 60.0

T = TypeVar("T")

_lock = threading.Lock()
_pool: ProcessPoolExecutor | None = None
_warm_pid: int | None = None
_last_pid: int | None = None


def _workers() -> int:
    raw = os.environ.get(WORKERS_ENV, "").strip()
    return DEFAULT_WORKERS if not raw else max(0, int(raw))


def _context() -> BaseContext:
    if "forkserver" not in multiprocessing.get_all_start_methods():
        return multiprocessing.get_context("spawn")
    context = multiprocessing.get_context("forkserver")
    context.set_forkserver_preload([__name__])
    return context


def start() -> int | None:
    """Start the pool and warm one worker; its pid, or None when switched off.

    Warmed now rather than on the first relight: starting the server process and
    importing the model costs about a second, and it should not be a visitor's.
    A pool that will not start is logged, and the light is computed here instead.
    """
    global _pool, _warm_pid
    workers = _workers()
    with _lock:
        if _pool is not None or workers == 0:
            return _warm_pid
        _pool = ProcessPoolExecutor(
            max_workers=workers, mp_context=_context(), max_tasks_per_child=JOBS_PER_WORKER
        )
        pool = _pool
    try:
        _warm_pid = int(pool.submit(os.getpid).result(timeout=WARM_TIMEOUT_S))
    except Exception:  # noqa: BLE001 - logged; the light is then computed here
        log.warning("the light worker did not start; computing in the serving process",
                    exc_info=True)
        stop()
    return _warm_pid


def stop() -> None:
    """Stop the pool, letting a relight that is running finish."""
    global _pool, _warm_pid
    with _lock:
        pool, _pool, _warm_pid = _pool, None, None
    if pool is not None:
        pool.shutdown(wait=True, cancel_futures=True)


def running() -> bool:
    return _pool is not None


def warm_pid() -> int | None:
    """The worker started at startup — for the startup log and the tests."""
    return _warm_pid


def last_worker_pid() -> int | None:
    """Which process computed the last light that went to the pool."""
    return _last_pid


def recompute_light(conn: sqlite3.Connection, garden_id: int) -> int:
    """`lighting.recompute_light`, in a worker when there is one."""
    return _isolated(conn, lighting.recompute_light, garden_id)


def month_grid(conn: sqlite3.Connection, garden: Garden, month: int) -> LightGrid | None:
    """`lightview.month_grid`, in a worker when there is one."""
    return _isolated(conn, lightview.month_grid, garden, month)


def database_file(conn: sqlite3.Connection) -> str | None:
    """The file behind a connection, or None when there is none to open elsewhere."""
    for row in conn.execute("PRAGMA database_list").fetchall():
        if row[1] == "main":
            return str(row[2]) or None
    return None


def _isolated(conn: sqlite3.Connection, job: Callable[..., T], *args: object) -> T:
    path = database_file(conn)
    pool = _pool
    if path is None or pool is None:
        return job(conn, *args)
    # The worker's connection is its own: a write this one still held would lock
    # it out for the busy timeout — and it could not see the write anyway.
    conn.commit()
    try:
        return _submit(pool, path, job, *args)
    except BrokenProcessPool:
        log.warning("a light worker died; replacing the pool and trying once more",
                    exc_info=True)
        _replace(pool)
        again = _pool
        if again is None:
            return job(conn, *args)
        return _submit(again, path, job, *args)


def _submit(pool: ProcessPoolExecutor, path: str, job: Callable[..., T], *args: object) -> T:
    global _last_pid
    pid, result = pool.submit(_in_worker, path, job, *args).result()
    _last_pid = pid
    return result


def _replace(broken: ProcessPoolExecutor) -> None:
    """A new pool for a broken one — once, however many requests saw it break."""
    with _lock:
        if _pool is not broken:
            return
    stop()
    start()


def _in_worker(path: str, job: Callable[..., T], *args: object) -> tuple[int, T]:
    """In the worker: a connection of its own, the job, and who computed it."""
    conn = connect(path)
    try:
        return os.getpid(), job(conn, *args)
    finally:
        conn.close()


__all__ = [
    "DEFAULT_WORKERS",
    "WORKERS_ENV",
    "database_file",
    "last_worker_pid",
    "month_grid",
    "recompute_light",
    "running",
    "start",
    "stop",
    "warm_pid",
]
