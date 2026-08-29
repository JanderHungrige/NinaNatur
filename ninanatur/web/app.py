"""NinaNatur web app.

Wave 1 serves only the branded shell and a health endpoint — deliberately no
product logic, so the deployment chain can be proven while there is nothing
complicated to confuse a diagnosis. Wave 2 mounts the /api/v1 router here.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ninanatur.api.gardens import router as gardens_router
from ninanatur.api.geo import router as geo_router
from ninanatur.api.planning import router as planning_router
from ninanatur.api.plants import router as plants_router
from ninanatur.ingest.catalogue import DEFAULT_CATALOGUE, sync_catalogue
from ninanatur.ingest.db import connect, database_path, init_schema
from ninanatur.version import app_version

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
    conn = connect(database_path(), same_thread=False)
    try:
        migrated = init_schema(conn)
        if migrated:
            print(f"schema migrated: {', '.join(migrated)}", flush=True)
        # A fresh volume has the schema but no plants, and the app then answers
        # "0 matching species" to every request. An *existing* volume has plants
        # but not the ones a newer image ships — which is how the insect group
        # breakdown went live in the image and stayed invisible in production.
        # Both are the same problem: the shipped catalogue is the truth, gardens
        # on the volume are not touched.
        synced = sync_catalogue(conn, DEFAULT_CATALOGUE)
        if synced:
            print(f"catalogue synced: {synced}", flush=True)
    finally:
        conn.close()
    yield


app = FastAPI(
    title="NinaNatur",
    version=app_version(),
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(plants_router)
app.include_router(gardens_router)
app.include_router(planning_router)
app.include_router(geo_router)


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
def healthz() -> JSONResponse:
    """Liveness probe for the deploy cron and the reverse proxy.

    Deliberately dependency-free: it must answer while the app is otherwise
    broken, or a failing deploy looks identical to a failing database.
    """
    return JSONResponse(
        {"status": "ok", "service": "ninanatur", "version": app_version()}
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
