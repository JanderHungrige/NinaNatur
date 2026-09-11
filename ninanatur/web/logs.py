"""What the log knows — Wave 20, feature 6.

Measured on 2026-09-11 before this: production's container log held a line for
every request with the visitor's full address and the whole path, and on the
garden routes the path *is* the share token — the one thing standing between a
garden and anybody holding the log. There was no logging configuration at all.

- **The access line is the app's own**, and names the route rather than the
  path: `/api/v1/gardens/{token}/light`, with an eight-character hash of the
  token so one garden's requests can still be followed. uvicorn's own access
  log is switched off (`--no-access-log`); it can only write the raw path.
- **Every token-shaped segment is masked again** in the formatter, whatever
  wrote the line — `upstream_failed` used to write the raw path into a warning.
- **A request id** comes in (kept when it is sane) or is made, goes back out as
  `X-Request-ID`, and is on every line written while the request runs.
- **A security channel** (`ninanatur.security`) for failed logins, refusals and
  server errors, so they can be found without reading every page view.
- **Addresses are kept only to their network** (/24, /48). The full address is
  held only in the rate-limit table, for minutes; a log is kept for weeks.

`log_config.json` wires this into uvicorn: JSON lines on stdout.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

ACCESS = logging.getLogger("ninanatur.access")
SECURITY = logging.getLogger("ninanatur.security")

#: `secrets.token_urlsafe(32)` is 43 characters; anything this long after
#: `/gardens/` is a token. `from-map` is not.
TOKEN_SEGMENT = re.compile(r"(/gardens/)[A-Za-z0-9_-]{16,}")
#: What an incoming `X-Request-ID` may look like to be kept: a proxy's id, not
#: a way to write into somebody else's log.
SANE_ID = re.compile(r"[A-Za-z0-9._-]{8,64}")

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def mask(text: str) -> str:
    return TOKEN_SEGMENT.sub(r"\1{token}", text)


def short_hash(text: str) -> str:
    """Eight hex characters: enough to follow one thing through a log, far too
    few to get back to it."""
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def network_of(address: str) -> str:
    """The /24 (IPv4) or /48 (IPv6) an address belongs to; anything else as is."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return address
    prefix = 24 if ip.version == 4 else 48
    return str(ipaddress.ip_network(f"{ip}/{prefix}", strict=False).network_address)


class RequestContext(logging.Filter):
    """Puts the running request's id on every record, whoever writes it."""

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "request_id", None) is None:
            record.request_id = _request_id.get()
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line, every string in it masked."""

    def format(self, record: logging.LogRecord) -> str:
        line: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": mask(record.getMessage()),
            "request_id": getattr(record, "request_id", None) or _request_id.get(),
        }
        for key, value in dict(getattr(record, "fields", None) or {}).items():
            line.setdefault(key, mask(value) if isinstance(value, str) else value)
        if record.exc_info:
            line["exc"] = mask(self.formatException(record.exc_info))
        return json.dumps(line, ensure_ascii=False, default=str)


def security_event(event: str, **fields: object) -> None:
    """A line on the security channel, carrying the running request's id."""
    SECURITY.warning("%s", event, extra={
        "fields": {"event": event, **fields}, "request_id": _request_id.get(),
    })


def _incoming_id(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"x-request-id":
            candidate = value.decode("latin-1")
            return candidate if SANE_ID.fullmatch(candidate) else None
    return None


def _route_of(scope: Scope) -> str:
    """The route's template where the router found one — the token masked by
    construction — and the masked path where it did not."""
    template = getattr(scope.get("route"), "path", None)
    if isinstance(template, str) and ":path}" not in template:
        return mask(template)
    return mask(str(scope.get("path", "")))


class AccessLog:
    """One line per request, and the request id in and out."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = _incoming_id(scope) or uuid.uuid4().hex[:16]
        context = _request_id.set(request_id)
        started = time.perf_counter()
        status = 500  # what a request that raises before answering becomes

        async def sending(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
                MutableHeaders(scope=message)["x-request-id"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, sending)
        finally:
            _write(scope, status, started, request_id)
            _request_id.reset(context)


def _write(scope: Scope, status: int, started: float, request_id: str) -> None:
    client = scope.get("client")
    token = dict(scope.get("path_params") or {}).get("token")
    fields = {
        "method": scope.get("method", ""),
        "path": _route_of(scope),
        "status": status,
        "ms": round((time.perf_counter() - started) * 1000),
        "client": network_of(str(client[0])) if client else "unknown",
        "garden": short_hash(str(token)) if token else None,
    }
    ACCESS.info("%s %s %s %sms", fields["method"], fields["path"], status, fields["ms"],
                extra={"fields": fields, "request_id": request_id})
    if status >= 500:
        security_event("server_error", method=fields["method"], path=fields["path"],
                       status=status, client=fields["client"])


__all__ = [
    "AccessLog",
    "JsonFormatter",
    "RequestContext",
    "mask",
    "network_of",
    "security_event",
    "short_hash",
]
