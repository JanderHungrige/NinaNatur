"""Suite-wide guard: no test reaches a state survey.

Until 2026-09-07 nothing needed this. A garden's stored coordinates were rounded
to 0.1°, so `ensure_terrain` refused to fetch and the whole elevation path was
inert under test. Raising the precision to four places woke it up, and a plain
`POST /light` in `test_light_api.py` started answering with a **real** 27×27
window off Berlin's survey — a test whose result depended on a WCS in Potsdam
being up, and on whether `data/cache` happened to hold the answer.

That is the exact failure `CLAUDE.md` names: a test that passes locally and
fails in CI is worse than no test. So the survey is switched off for every test
by default, in the one honest way the code already supports — *no service for
this state*, which nine Bundesländer really are.

A test that wants ground saves a window with `save_window` and reads it back;
that path is offline by construction. A test that wants to exercise the fetch
itself patches `terrain_sync.state_at` and `terrain_sync.fetch_window` for its
own scope, as `test_terrain_sync.py` does — a local patch beats this one because
it is applied later.
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest

# Never the developer's own HTTP cache. `data/cache` holds real answers from
# real services, so a test that reached the network by accident passed on any
# machine that had once fetched the same thing — and failed in CI, which has no
# cache. That hid a Nominatim call on the light-map path for a whole wave
# (2026-09-21). An empty cache makes a local run fail exactly where CI would.
os.environ["NINANATUR_CACHE_DIR"] = tempfile.mkdtemp(prefix="ninanatur-test-cache-")

# The names the app answers to, plus `testserver` — the Host every TestClient
# sends. Set here, before any test module imports the app, because the list is
# read once at import. Production never sees this value: the image's default
# names only the real domains, localhost and the loopback address.
os.environ.setdefault(
    "NINANATUR_ALLOWED_HOSTS",
    "ninanatur.w3rth.de,ninanatur-dev.w3rth.de,localhost,127.0.0.1,testserver",
)


#: Every sync that asks which state a garden is in before it fetches anything.
#: Each one reverse-geocodes against Nominatim, so each one is switched off here
#: — and `test_no_network.py` fails if a module starts calling `state_at` without
#: being added, because that is how the point-cloud sync slipped past this list
#: when Wave 25 wrote it: two names here, three callers in the code.
SURVEYING = ("terrain_sync", "building_sync", "cloud_sync")


@pytest.fixture(autouse=True)
def _no_state_surveys(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    import importlib

    for name in SURVEYING:
        module = importlib.import_module(f"ninanatur.garden.{name}")
        monkeypatch.setattr(module, "state_at", lambda *_a, **_k: None)
    yield


#: Where the garden's surroundings are fetched from Overpass (doc 114): at the
#: map import and on the shade rebuild, both through this one module. Its two
#: fetches answer "nothing mapped here" in every test that does not ask for
#: more, so a map import stubbed for buildings and streets alone never reaches
#: out for the land around it — `test_no_network.py` holds this name to the code.
LANDCOVER_FETCHING = "ninanatur.garden.landcover_sync"


@pytest.fixture(autouse=True)
def _no_landcover(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    import importlib
    from contextlib import nullcontext

    module = importlib.import_module(LANDCOVER_FETCHING)
    monkeypatch.setattr(module, "landcover_in", lambda *_a, **_k: [])
    monkeypatch.setattr(module, "streets_in", lambda *_a, **_k: [])
    # The background tasks open a connection of their own, to the configured
    # database — in a test, the developer's. Here they get none and do nothing;
    # a test of that path hands them its own connection.
    monkeypatch.setattr(module, "background_connection", lambda: nullcontext(None))
    module._failed_at.clear()
    yield
    assert not module._running, "a background fetch did not let go of its claim"
