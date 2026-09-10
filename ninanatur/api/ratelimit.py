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
import time

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


__all__ = ["LIMITS", "REFUSAL", "check", "client_of"]
