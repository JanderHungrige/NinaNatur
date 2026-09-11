"""Where a request comes from, for the routes that act on a login — Wave 20, feature 9.

The session cookie is `SameSite=Lax`, which keeps it off every request another
*site* makes. But to a browser a site is the registrable domain, `w3rth.de`, and
this host serves three other projects under it: their pages are the same site
as this one, and their requests carry the cookie. A JSON body forces a CORS
preflight, which fails; a POST without a body does not — and
`POST /gardens/{token}/claim` is exactly that.

So every route that changes something on behalf of a login checks where the
request came from. One that names an origin must name this host; one the browser
marks as coming from another site — the same site included — is refused. A
request with neither header is a script or a test rather than a browser acting
for somebody, and is let through: every browser sends at least one of them.
"""
from __future__ import annotations

from urllib.parse import urlparse

from fastapi import HTTPException, Request, status

from ninanatur.api.ratelimit import client_of
from ninanatur.web.logs import network_of, security_event

NOT_HERE = "Diese Anfrage kam nicht von dieser Seite."
#: What `Sec-Fetch-Site` says when the request was not made by this page itself.
ELSEWHERE = frozenset({"same-site", "cross-site"})


def same_origin(request: Request) -> None:
    """Refuse a login-acting request that another page made. A dependency."""
    origin = request.headers.get("origin")
    fetch_site = request.headers.get("sec-fetch-site")
    foreign = origin is not None and urlparse(origin).hostname != request.url.hostname
    if foreign or fetch_site in ELSEWHERE:
        # The route's template, never its path: on a garden route that is the token.
        route = str(getattr(request.scope.get("route"), "path", ""))
        security_event("foreign_origin", path=route, origin=origin or "",
                       fetch_site=fetch_site or "", client=network_of(client_of(request)))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=NOT_HERE)


__all__ = ["ELSEWHERE", "NOT_HERE", "same_origin"]
