"""NinaNatur web app.

Wave 1 serves only the branded shell and a health endpoint — deliberately no
product logic, so the deployment chain can be proven while there is nothing
complicated to confuse a diagnosis. Wave 2 mounts the /api/v1 router here.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).parent / "static"
VERSION = "0.1.0"

app = FastAPI(title="NinaNatur", version=VERSION, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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
