"""Every route the app answers — walked the way the API document walks them.

FastAPI 0.141 stopped flattening included routers into `app.routes`: each sits
there as one opaque entry, and a loop over `app.routes` meets three routes of
forty-five — `/healthz` and the preview's two documentation routes, none of
which writes anything. A guard written that way passes by checking nothing.
`test_sessions_end`'s walker did, from the day it was written until Wave 20's
feature 0 found it.

`iter_route_contexts` is what `get_openapi` itself walks, so a route this misses
is a route the API document misses too — and the walk refuses to answer at all
if it stops reaching routes that are always there.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.routing import iter_route_contexts

#: Routes that exist whatever else changes. A walk that does not meet them is
#: broken, and every guard built on it would pass without looking.
LANDMARKS = frozenset({
    "/healthz",
    "/api/v1/sessions",
    "/api/v1/gardens/{token}",
    "/api/v1/gardens/{token}/beds/{bed_id}/suggestions",
})

WRITES = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def api_routes(app: FastAPI) -> list[Any]:
    """Each route with its full path, its methods and its dependency tree."""
    found = [c for c in iter_route_contexts(app.routes)
             if getattr(c, "dependant", None) is not None]
    missing = LANDMARKS - {c.path for c in found}
    assert not missing, f"the route walk no longer reaches {sorted(missing)}"
    return found


def path_ids(route: Any) -> list[str]:
    """The path parameters a route takes, the share token aside."""
    return [p.name for p in route.dependant.path_params if p.name != "token"]


def takes_token(route: Any) -> bool:
    return any(p.name == "token" for p in route.dependant.path_params)
