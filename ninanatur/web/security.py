"""What the app says about itself — and what it lets a browser do with it.

Wave 20, feature 3. Measured on 2026-09-10 before any of this existed: the live
site sent no security header at all (Nginx Proxy Manager adds only `Server` and
`X-Served-By`), `/openapi.json` and `/api/docs` answered anybody, an unreachable
upstream came back as a bare 500, and an upstream answering HTML instead of JSON
came back as a **422 carrying the parser's message** — blaming the caller for
somebody else's outage, in words that described our code.

`install` wires all of it into the app. Kept apart from `web/app.py`, which is
about what the app *is*; this is about what it admits to.
"""
from __future__ import annotations

import json
import logging
import os
from urllib.parse import urlparse

import requests
from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ninanatur.geo.orthophotos import ORTHOPHOTOS
from ninanatur.ingest.http import HttpError
from ninanatur.web.environment import is_production
from ninanatur.web.logs import mask

log = logging.getLogger(__name__)

#: The names the app answers to. A request for any other Host is refused with a
#: 400 before it reaches a route, so a forged Host cannot steer anything that
#: builds a URL from it. The container's healthcheck asks 127.0.0.1; the Vite
#: dev server forwards as localhost.
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "NINANATUR_ALLOWED_HOSTS",
        "ninanatur.w3rth.de,ninanatur-dev.w3rth.de,localhost,127.0.0.1",
    ).split(",")
    if host.strip()
]

#: Where the plan's pictures come from. The map picker draws OpenStreetMap's
#: tiles; the species panel shows Wikipedia's thumbnails — from `thumb.` as often
#: as `upload.`, which a policy naming only one would have silently blanked.
MAP_TILES = "https://tile.openstreetmap.org"
PLANT_PHOTOS = ("https://upload.wikimedia.org", "https://thumb.wikimedia.org")


def _origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def content_security_policy() -> str:
    """Exactly what the built page loads, and nothing it does not.

    The aerial imagery is loaded by the browser straight from each state's WMS
    service, so those origins are read from the registry: a state added there
    appears here without anybody remembering to. No `unsafe-inline`: the bundle
    is one module script and one stylesheet, both files, and React's `style=`
    props go through the CSSOM, which a policy does not govern.
    """
    aerial = sorted({_origin(service.url) for service in ORTHOPHOTOS})
    images = " ".join(["'self'", MAP_TILES, *PLANT_PHOTOS, *aerial])
    return "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        f"img-src {images}",
        "media-src 'self'",
        "connect-src 'self'",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ])


POLICY = content_security_policy()

#: Swagger UI, which only the preview serves, loads from a CDN and runs an inline
#: script. It gets its own looser policy, on its own path, rather than loosening
#: the one the garden is drawn under.
DOCS_PATH = "/api/docs"
DOCS_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    "img-src 'self' data: https://fastapi.tiangolo.com",
    "frame-ancestors 'none'",
])

FIXED_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    # Nothing embeds this app, and a framed garden is a clickjacked garden.
    "X-Frame-Options": "DENY",
    # Not `no-referrer`: OpenStreetMap's tile policy asks for a Referer, and
    # the origin alone is all this sends across sites.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    # The clipboard stays allowed — the garden link is copied with it.
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
}

#: HSTS belongs where TLS is. The app sets it only when the trusted proxy says
#: the request arrived over https, so a plain-http development server never
#: tells a browser to refuse it.
HSTS = "max-age=31536000"


async def guard_every_answer(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Add the headers to every response — errors, refusals and files included."""
    response = await call_next(request)
    for name, value in FIXED_HEADERS.items():
        response.headers.setdefault(name, value)
    response.headers["Content-Security-Policy"] = (
        DOCS_POLICY if request.url.path == DOCS_PATH else POLICY
    )
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = HSTS
    return response


UPSTREAM_DOWN = (
    "Ein externer Dienst antwortet gerade nicht. Bitte versuche es später noch einmal."
)


async def upstream_failed(request: Request, exc: Exception) -> JSONResponse:
    """Somebody else's outage: a 502 that names nobody.

    Logged in full with its context — the URL, the upstream status, the parser's
    complaint are exactly what a person debugging it needs — and none of it sent
    to the caller, who did nothing wrong and should not learn which services
    this app leans on. `JSONDecodeError` is a `ValueError`, which is why it used
    to fall through to the 422 handler meant for the domain's own refusals.
    """
    log.warning("upstream failure on %s %s: %r", request.method, mask(request.url.path), exc)
    return JSONResponse(status_code=502, content={"detail": UPSTREAM_DOWN})


def _not_found() -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Not Found"})


def install_docs(app: FastAPI) -> None:
    """The API description, on the preview only.

    Decided per request rather than at import, so one image serves both
    environments and a test can ask either. `app.openapi()` still works
    everywhere — the frontend's type generation calls it directly.
    """

    @app.get("/openapi.json", include_in_schema=False)
    def openapi_document() -> Response:
        return _not_found() if is_production() else JSONResponse(app.openapi())

    @app.get(DOCS_PATH, include_in_schema=False)
    def api_docs() -> Response:
        if is_production():
            return _not_found()
        return get_swagger_ui_html(openapi_url="/openapi.json", title="NinaNatur API")


def install(app: FastAPI) -> None:
    """Wire the headers, the host check, the upstream handling and the docs.

    Order matters and is Starlette's: the middleware added last runs first. The
    host check goes in before the header guard, so the guard wraps it and even
    its 400 carries the headers.
    """
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS, www_redirect=False)
    app.middleware("http")(guard_every_answer)
    for failure in (HttpError, requests.RequestException, json.JSONDecodeError):
        app.add_exception_handler(failure, upstream_failed)
    install_docs(app)


__all__ = ["ALLOWED_HOSTS", "POLICY", "content_security_policy", "install"]
