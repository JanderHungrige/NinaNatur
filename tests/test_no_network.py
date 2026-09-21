"""No test reaches the network — held by the suite itself, not by care.

Until Wave 20's feature 0 this was a convention: outbound calls go through
`ingest/http.py`, tests stub what they know about, and a conftest fixture stops
the state surveys. Nothing stopped the call nobody knew about — it would simply
have been made, answered from a warm disk cache on one machine and by the
internet in CI, and a test that depends on either is not a test.

`pytest-socket` now refuses every socket that is not a Unix one
(`pyproject.toml`: `--disable-socket --allow-unix-socket`). The Unix ones stay:
the light worker's forkserver and every event loop talk over them.
"""
from __future__ import annotations

import os
import re
import socket
from pathlib import Path

import pytest
from pytest_socket import SocketBlockedError

pytestmark = [
    pytest.mark.gate,
    # Said by pytest-socket as it refuses — which is what these tests are for.
    pytest.mark.filterwarnings("ignore:A test tried to use socket:UserWarning"),
]

#: TEST-NET-1 (RFC 5737): an address that is never routed. Without the guard
#: this test would time out rather than connect — and fail, which is the point.
NOWHERE = ("192.0.2.1", 80)


def test_a_test_cannot_open_a_connection() -> None:
    with pytest.raises(SocketBlockedError):
        socket.create_connection(NOWHERE, timeout=1)


def test_nor_can_the_app_s_own_http_client() -> None:
    """The one door every outbound call goes through."""
    import requests

    with pytest.raises(SocketBlockedError):
        requests.get("http://192.0.2.1/", timeout=1)


def test_a_unix_socket_is_still_allowed() -> None:
    """The light worker's forkserver and the event loop need them."""
    left, right = socket.socketpair()
    left.sendall(b"ok")
    assert right.recv(2) == b"ok"
    left.close()
    right.close()


# --- The switches in conftest cover what they claim to -----------------------
#
# A guard that is a list goes stale the day somebody adds to the code and not to
# the list. Wave 25 wrote a third sync that asks Nominatim which state a garden
# is in; conftest's guard named two. Nothing failed locally, because a
# developer's HTTP cache already held the answer — and the whole light-map API
# went red the first time the wave reached CI (2026-09-21). So the list is
# checked against the code rather than trusted.

GARDEN = Path(__file__).resolve().parent.parent / "ninanatur" / "garden"


def test_every_sync_that_asks_which_state_it_is_in_is_switched_off() -> None:
    """Self-consistency, as CLAUDE.md asks: the guard agrees with the code it
    guards, so adding a caller without adding it fails *here*, locally, rather
    than in CI where the socket is refused."""
    from conftest import SURVEYING

    calling = {
        path.stem for path in GARDEN.glob("*.py")
        if re.search(r"^from ninanatur\.geo\.osm import .*\bstate_at\b",
                     path.read_text(), re.M)
    }
    assert calling == set(SURVEYING), (
        f"call state_at but are not switched off in conftest: "
        f"{sorted(calling - set(SURVEYING))}; switched off but no longer calling "
        f"it: {sorted(set(SURVEYING) - calling)}")


def test_no_test_reads_the_developers_own_http_cache() -> None:
    """`data/cache` holds real answers from real services. A test that reached
    the network by mistake passed on any machine that had fetched the same
    thing once, and failed in CI, which has none."""
    here = Path(os.environ["NINANATUR_CACHE_DIR"]).resolve()
    assert here.name.startswith("ninanatur-test-cache-")
    assert here != (Path(__file__).resolve().parent.parent / "data" / "cache").resolve()
