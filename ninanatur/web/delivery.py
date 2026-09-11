"""What the site sends, and how long a browser may keep it.

Measured on the preview on 2026-09-11. Nothing was compressed: a 200-row plant
search went out as 115 KB of JSON and the bundle as 271 KB, gzip asked for or
not — Nginx Proxy Manager passes on what the app sends. And nothing said how
long it might be kept: the bundle, whose name is a hash of its content, was
asked for again; the page that names it was left to heuristic caching, which can
hold an `index.html` naming a bundle the next deployment no longer ships.

Compression is the app's rather than the proxy's, so it holds on the direct port
and in every test as well. Film, pictures and fonts are left alone — they are
compressed already, and a video is played through range requests whose byte
offsets gzip would break; Starlette's defaults exclude exactly those types.

BREACH, the attack on compressed HTTPS, needs a secret and something the
attacker chooses in the same response. The answers that carry a share token — a
garden, the list of one's own gardens — reflect nothing a stranger can put
there, and the session cookie travels in headers, which gzip does not touch.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

#: Below this the header costs more than compression saves.
MIN_BYTES = 1000
#: Level 6 rather than Starlette's 9: within a few per cent of the size for a
#: fraction of the CPU, on two cores shared with three other projects.
LEVEL = 6

#: For files whose name is a hash of their content. A new build names a new
#: file, so there is never anything to ask about again.
IMMUTABLE = "public, max-age=31536000, immutable"
#: For everything else, above all the page that names the hashed files: it may
#: be kept, but is asked about every time — a 304 when nothing changed.
REVALIDATE = "no-cache"
#: Where Vite puts what it hashes.
HASHED = "assets/"


def compress(app: FastAPI) -> None:
    """Compress answers for every browser that asks for it."""
    app.add_middleware(GZipMiddleware, minimum_size=MIN_BYTES, compresslevel=LEVEL)


class BuiltBundle(StaticFiles):
    """The built front end, each file saying how long it may be kept."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        # Only a file that was there. A 404 kept for a year would outlive the
        # deployment race that caused it.
        hashed = path.startswith(HASHED) and response.status_code < 400
        response.headers["Cache-Control"] = IMMUTABLE if hashed else REVALIDATE
        return response


def serve_bundle(app: FastAPI, directory: Path) -> bool:
    """Mount the built front end at "/", if one was built. Returns whether it was.

    Mount it last, so /api/v1 and /healthz keep priority. With html=True a mount
    at "/" answers anything unmatched with the page and a 200 — which would make
    the deploy cron's health probe pass on a broken app, far worse than a 404.
    """
    if not directory.is_dir():
        return False
    app.mount("/", BuiltBundle(directory=directory, html=True), name="app")
    return True


__all__ = ["IMMUTABLE", "REVALIDATE", "BuiltBundle", "compress", "serve_bundle"]
