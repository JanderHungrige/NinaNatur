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
from collections.abc import Iterator

import pytest

# The names the app answers to, plus `testserver` — the Host every TestClient
# sends. Set here, before any test module imports the app, because the list is
# read once at import. Production never sees this value: the image's default
# names only the real domains, localhost and the loopback address.
os.environ.setdefault(
    "NINANATUR_ALLOWED_HOSTS",
    "ninanatur.w3rth.de,ninanatur-dev.w3rth.de,localhost,127.0.0.1,testserver",
)


@pytest.fixture(autouse=True)
def _no_state_surveys(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    from ninanatur.garden import building_sync, terrain_sync

    monkeypatch.setattr(terrain_sync, "state_at", lambda *_a, **_k: None)
    monkeypatch.setattr(building_sync, "state_at", lambda *_a, **_k: None)
    yield
