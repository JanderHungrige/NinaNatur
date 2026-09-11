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

import socket

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
