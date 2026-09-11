"""NinaNatur web app.

Wave 1 serves only the branded shell and a health endpoint — deliberately no
product logic, so the deployment chain can be proven while there is nothing
complicated to confuse a diagnosis. Wave 2 mounts the /api/v1 router here.
"""
from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from ninanatur.api.accounts import router as accounts_router
from ninanatur.api.canopies import router as canopies_router
from ninanatur.api.elements import router as elements_router
from ninanatur.api.feedback import router as feedback_router
from ninanatur.api.gardens import router as gardens_router
from ninanatur.api.geo import router as geo_router
from ninanatur.api.light import router as light_router
from ninanatur.api.planning import router as planning_router
from ninanatur.api.plants import router as plants_router
from ninanatur.garden import light_worker
from ninanatur.ingest.catalogue import DEFAULT_CATALOGUE, sync_catalogue
from ninanatur.ingest.db import connect, database_path, enable_wal, init_schema
from ninanatur.ops.backup import default_dest, snapshot_before_migration
from ninanatur.version import app_version
from ninanatur.web.environment import environment
from ninanatur.web.logs import AccessLog
from ninanatur.web.security import install as install_security

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
# The built frontend, present only in the container image. Vite serves it in
# development, so its absence here is normal rather than an error.
DIST_DIR = Path(__file__).parent / "dist"

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Ensure the schema exists and the catalogue is present before serving.

    Two separate failures both showed up only in a real deployment: tables were
    created solely by the ingest CLI, so a fresh container answered 500 to every
    write; and even with a schema, a fresh volume had no plants, so every
    suggestion list came back empty.

    Both steps are idempotent — CREATE TABLE IF NOT EXISTS, and seeding only when
    there are no taxa at all, so a newer local ingest is never overwritten.
    """
    path = database_path()
    # Before anything touches the file, and before migrations run: a migration
    # that fails halfway must leave something to go back to. A fresh volume has
    # nothing to copy. A failed copy is reported loudly and does not stop the
    # app — the nightly backups still exist, and a site that will not start is
    # the worse outcome.
    try:
        taken = snapshot_before_migration(path, default_dest(path))
        if taken is not None:
            log.info("database copied before migrating: %s", taken.name)
    except Exception as exc:  # noqa: BLE001 - logged with context, startup goes on
        log.warning("pre-migration backup of %s failed: %r", path, exc)

    conn = connect(path, same_thread=False)
    try:
        migrated = init_schema(conn)
        if migrated:
            log.info("schema migrated: %s", ", ".join(migrated))
        # After the pre-migration copy and the migrations, so both still ran
        # against the file exactly as the previous release left it.
        mode = enable_wal(conn)
        if mode != "wal":
            log.warning("database stayed in journal mode %r, not WAL", mode)
        # A fresh volume has the schema but no plants, and the app then answers
        # "0 matching species" to every request. An *existing* volume has plants
        # but not the ones a newer image ships — which is how the insect group
        # breakdown went live in the image and stayed invisible in production.
        # Both are the same problem: the shipped catalogue is the truth, gardens
        # on the volume are not touched.
        synced = sync_catalogue(conn, DEFAULT_CATALOGUE)
        if synced:
            log.info("catalogue synced: %s", synced)
    finally:
        conn.close()
    # The light is computed in processes of their own; see `light_worker`.
    worker = light_worker.start()
    if worker is not None:
        log.info("light worker ready: pid %s", worker)
    try:
        yield
    finally:
        light_worker.stop()


app = FastAPI(
    title="NinaNatur",
    version=app_version(),
    # Served by `web/security.py` instead, on the preview only. FastAPI's own
    # routes would publish the whole API surface on the live site.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(plants_router)
app.include_router(gardens_router)
app.include_router(elements_router)
app.include_router(planning_router)
app.include_router(geo_router)
app.include_router(accounts_router)
app.include_router(feedback_router)
app.include_router(light_router)
app.include_router(canopies_router)


#: Who may say, in `X-Forwarded-For` and `X-Forwarded-Proto`, who the visitor
#: was and how they connected.
#:
#: Nginx Proxy Manager reaches the app through the Docker network's gateway —
#: measured on the host as 172.27.0.1 for production and 172.30.0.1 for the
#: preview — not through 172.17.0.1, which is where the port is *published*.
#: uvicorn's default trusted only 127.0.0.1, so the app believed nobody: every
#: visitor was the proxy, and the login limit put the whole site in one bucket.
#:
#: Docker's default address pools are inside 172.16.0.0/12, and since the port
#: is bound to the bridge only, nothing else can connect. The middleware takes
#: the rightmost address the trusted proxies did not vouch for — the one a
#: visitor cannot write. Never "*": that takes the leftmost, which anybody can.
TRUSTED_PROXIES = os.environ.get("NINANATUR_TRUSTED_PROXIES", "127.0.0.1,172.16.0.0/12")


#: The largest request body the API reads, in bytes. The biggest legitimate one
#: is a 500-corner outline, around 15 KB; a bed polygon used to be accepted at
#: 2.8 MB before anything looked at it.
MAX_BODY_BYTES = 1_000_000


@app.middleware("http")
async def body_has_an_edge(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Refuse an oversized body before it is read, parsed or validated.

    Declared by Content-Length; a body sent without one is still bounded by the
    schema limits behind this, which is where the real edges are.
    """
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        return JSONResponse(status_code=413, content={"detail": "Anfrage zu groß"})
    return await call_next(request)


# Headers, allowed hosts, upstream failures and the preview-only API docs —
# see `web/security.py`. Installed after the body limit so its guard wraps the
# 413 too.
install_security(app)

# Last, so it runs first: every later decision — the rate-limit key, the
# cookie's Secure flag, HSTS — needs the visitor's address and scheme already
# rewritten from the trusted proxy's headers.
# Inside the proxy-header rewrite, so it records the visitor's network rather
# than the proxy's; outside everything else, so the 400s and 413s the
# middleware above answer are logged too. See `web/logs.py`.
app.add_middleware(AccessLog)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=TRUSTED_PROXIES)


@app.exception_handler(ValueError)
async def value_error_is_422(_: Request, exc: ValueError) -> JSONResponse:
    """A validation failure must never surface as a 500.

    Handlers raise ValueError for domain-level validation; without this backstop a
    new raise site downstream escapes as an opaque 500 with the reason visible
    only in the log. Placed below FastAPI's own validation, which already returns
    422 for type and range errors.
    """
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/healthz")
async def healthz() -> JSONResponse:
    """Liveness probe for the deploy cron and the reverse proxy.

    Deliberately dependency-free: it must answer while the app is otherwise
    broken, or a failing deploy looks identical to a failing database. And
    async, so it runs on the event loop rather than in the thread pool the
    expensive computations fill — a busy app must not look like a dead one.
    """
    return JSONResponse(
        {
            "status": "ok",
            "service": "ninanatur",
            "version": app_version(),
            # Which deployment this is. The frontend reads it from here rather
            # than from its own build, because only the server knows.
            "environment": environment(),
        }
    )


if DIST_DIR.is_dir():
    # Mounted last so /api/v1 and /healthz keep priority. With html=True a
    # mount at "/" answers anything unmatched with the SPA shell and a 200 —
    # which would make the deploy cron's health probe start passing on a broken
    # app, and that is far worse than a 404.
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="app")
else:

    @app.get("/")
    def index() -> FileResponse:
        """Development fallback: the Wave 1 page, when no bundle has been built."""
        return FileResponse(STATIC_DIR / "index.html")
