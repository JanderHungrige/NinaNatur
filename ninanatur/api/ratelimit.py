"""How often one visitor may ask for something that costs.

Kept in SQLite, not in the process. The first version was a dict in
`accounts.py`: every image roll emptied it, and — worse — it keyed on the proxy's
address, because the app did not believe the proxy's forwarded headers, so every
visitor on the site shared one bucket. Ten wrong passwords from anybody locked
everybody out of logging in for five minutes.

The key is `request.client.host`, which `web.app` rewrites from the proxy's
`X-Forwarded-For` — and only when the request comes from a trusted proxy, and
only the rightmost address that proxy did not itself vouch for. That is the one
value in the header a visitor cannot choose.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException, Request, status

#: Bucket → (most requests, window in seconds). Generous for a person using the
#: page, and a wall for a script: the three expensive routes need no account and
#: each can cost seconds of CPU and an outbound survey or Overpass query.
LIMITS: dict[str, tuple[int, float]] = {
    "register": (10, 300.0),
    "login": (10, 300.0),
    "light": (30, 600.0),
    "recompute": (30, 600.0),
    "from-map": (10, 600.0),
    # A month view is looked at, not pressed: eight months, clicked through a
    # few times, is well inside it.
    "month": (60, 600.0),
}

REFUSAL = "Zu viele Anfragen. Bitte warte ein paar Minuten."


def client_of(request: Request) -> str:
    """Who is asking. Already the visitor's address, not the proxy's — see above."""
    return request.client.host if request.client else "unknown"


def check(conn: sqlite3.Connection, request: Request, bucket: str) -> None:
    """Count this request against its bucket, or refuse it with a 429.

    Wall-clock time rather than monotonic: the count has to survive the process,
    and a monotonic clock starts again with it.
    """
    limit, window = LIMITS[bucket]
    now = time.time()
    who = client_of(request)
    conn.execute("DELETE FROM rate_limit WHERE bucket = ? AND at < ?", (bucket, now - window))
    seen = conn.execute(
        "SELECT count(*) FROM rate_limit WHERE bucket = ? AND client = ?", (bucket, who)
    ).fetchone()[0]
    if seen >= limit:
        conn.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=REFUSAL)
    conn.execute("INSERT INTO rate_limit (bucket, client, at) VALUES (?, ?, ?)", (bucket, who, now))
    conn.commit()


# --- how much may run at once, whoever is asking ------------------------------

#: One per core on the host (two). The expensive routes are CPU-bound for
#: seconds; more at once than there are cores only makes each of them slower
#: while the thread pool fills and the cheap page loads queue behind them.
HEAVY_SLOTS = 2
HEAVY = threading.BoundedSemaphore(HEAVY_SLOTS)
#: Roughly one computation's worth of waiting.
RETRY_AFTER_S = 10
BUSY = "Gerade wird schon viel gerechnet. Bitte versuch es in ein paar Sekunden noch einmal."


@contextmanager
def heavy() -> Iterator[None]:
    """A slot for one expensive computation, or a 429 at once rather than a queue.

    Given back however the computation ends — a crash that kept its slot would
    shrink the house by one each time until it answered nobody.
    """
    if not HEAVY.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=BUSY,
            headers={"Retry-After": str(RETRY_AFTER_S)},
        )
    try:
        yield
    finally:
        HEAVY.release()


def heavy_slot() -> Iterator[None]:
    """`heavy` as a dependency, for a route that always computes.

    A dependency rather than code in the handler, so it is taken before the
    handler's own rate-limit check: a visitor turned away because the house is
    full has not used up any of their own allowance. A route that computes only
    sometimes — the month view — takes `heavy` itself, in the same order.
    """
    with heavy():
        yield


__all__ = [
    "BUSY", "HEAVY", "HEAVY_SLOTS", "LIMITS", "REFUSAL", "RETRY_AFTER_S",
    "check", "client_of", "heavy", "heavy_slot",
]
