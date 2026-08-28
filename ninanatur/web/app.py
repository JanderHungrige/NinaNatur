"""NinaNatur web app.

Wave 1 serves only the branded shell and a health endpoint — deliberately no
product logic, so the deployment chain can be proven while there is nothing
complicated to confuse a diagnosis. Wave 2 mounts the /api/v1 router here.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ninanatur.api.gardens import router as gardens_router
from ninanatur.api.plants import router as plants_router

STATIC_DIR = Path(__file__).parent / "static"
VERSION = "0.1.0"

app = FastAPI(title="NinaNatur", version=VERSION, docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(plants_router)
app.include_router(gardens_router)


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
    return JSONResponse({"status": "ok", "service": "ninanatur", "version": VERSION})


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
