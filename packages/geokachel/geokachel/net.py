"""Asking a state surveying office for something, politely.

The library never fetches anything itself: every function that needs bytes
takes a callable and the caller decides what it does. This is the default one,
for callers who would rather not write it — and the CLI uses it.

**Politeness is not a nicety here.** Sixteen state surveying offices publish
this data at their own expense, with no quota and no key and no contract. One
request per place per product, a pause between them, a User-Agent that says who
is asking, and a size cap so a mistake cannot pull a gigabyte. A library that
makes it easy to hammer them is a library that gets them closed.

Set `geokachel.net.USER_AGENT` to something with your own contact in it before
you fetch anything in anger. The default says it is a default.
"""
from __future__ import annotations

import os
import time

import requests

#: Say who is asking. A surveying office that needs to reach whoever is pulling
#: a thousand tiles has no other way. Set `GEOKACHEL_USER_AGENT`, or assign to
#: this, before fetching anything in anger — the default says it is a default.
USER_AGENT = os.environ.get("GEOKACHEL_USER_AGENT") or (
    "geokachel/0.1 (+https://github.com/werthvoll/NinaNatur; "
    "set GEOKACHEL_USER_AGENT to your own contact)")

#: Between requests. These are public offices, not an API.
DELAY_S = 0.5

#: (connect, read). A gigabyte-scale archive is read by range, never whole, so
#: the read timeout only has to cover one chunk.
TIMEOUT: tuple[float, float] = (5.0, 60.0)

#: The most any single whole-document fetch may be. A tile is megabytes and an
#: index is tens of megabytes; a gigabyte is a mistake, and the point of a cap
#: is to make the mistake loud rather than slow.
MAX_BYTES = 200_000_000


class FetchError(RuntimeError):
    """A request that did not answer, or answered with too much."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    return {"User-Agent": USER_AGENT, **(extra or {})}


def get_bytes(url: str, *, max_bytes: int = MAX_BYTES) -> bytes:
    """A whole document, refused the moment it passes the cap.

    The declared length is checked before a byte is read, and the body is
    dropped as it grows past the cap — a too-large answer does not get smaller
    on the second asking, so it is not retried.
    """
    time.sleep(DELAY_S)
    response = requests.get(url, headers=_headers(), timeout=TIMEOUT, stream=True)
    try:
        if response.status_code >= 400:
            raise FetchError(f"GET {url} refused: {response.status_code}",
                             status=response.status_code)
        declared = response.headers.get("Content-Length", "")
        if declared.isdigit() and int(declared) > max_bytes:
            raise FetchError(f"GET {url} announced {int(declared):,} bytes; "
                             f"the cap is {max_bytes:,}")
        body = bytearray()
        for chunk in response.iter_content(chunk_size=1 << 16):
            body += chunk
            if len(body) > max_bytes:
                raise FetchError(f"GET {url} passed its cap of {max_bytes:,} bytes")
        return bytes(body)
    finally:
        response.close()


def get_range(url: str, start: int, end: int) -> bytes:
    """The bytes from `start` to `end` inclusive, as HTTP counts them.

    A host that ignores the header and sends the whole file answers 200 rather
    than 206, and that is refused: silently reading a gigabyte where five
    megabytes were asked for is the failure this exists to avoid. Several of
    these portals do exactly that, so the refusal is load-bearing.
    """
    time.sleep(DELAY_S)
    response = requests.get(url, headers=_headers({"Range": f"bytes={start}-{end}"}),
                            timeout=TIMEOUT, stream=True)
    try:
        if response.status_code == 200:
            raise FetchError(f"{url} ignored the range and offered all of it", status=200)
        if response.status_code >= 400:
            raise FetchError(f"GET {url} bytes {start}-{end} refused: "
                             f"{response.status_code}", status=response.status_code)
        return response.content
    finally:
        response.close()


def size_of(url: str) -> int:
    """How large the thing at this address is, without fetching it."""
    length = presence(url)
    if length is None:
        raise FetchError(f"{url} does not say how large it is")
    return length


def presence(url: str) -> int | None:
    """Whether this address answers at all, and how large it says it is.

    A different question from `size_of`, and the difference is real: Bayern's
    laser host answers a HEAD with 200 and no `Content-Length` at all, so a
    check that read silence as absence would report a healthy source gone.
    Raises when nothing answers; returns None when something answers and will
    not say how much.
    """
    time.sleep(DELAY_S)
    response = requests.head(url, headers=_headers(), timeout=TIMEOUT,
                             allow_redirects=True)
    if response.status_code >= 400:
        raise FetchError(f"HEAD {url} refused: {response.status_code}",
                         status=response.status_code)
    length = response.headers.get("Content-Length")
    return int(length) if length is not None else None


__all__ = [
    "DELAY_S",
    "MAX_BYTES",
    "TIMEOUT",
    "USER_AGENT",
    "FetchError",
    "get_bytes",
    "get_range",
    "presence",
    "size_of",
]
