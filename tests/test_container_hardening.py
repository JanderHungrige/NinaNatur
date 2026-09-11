"""Locked and signed — Wave 20, feature 7, part 3: the container may do what the app needs.

Before 2026-09-11 the app's container ran with Docker's defaults: a writable
root filesystem, the default capability set, and no limit on memory or
processes on a 4 GB host it shares with three other projects. Measured before
choosing anything: the running app writes outside its volume only to `/tmp`
(the light worker's socket), and two relights of an 87-element garden plus a
month view peaked at 223 MiB.

Self-consistency, per CLAUDE.md: that the compose file says it, and that what it
says agrees with what the app is configured to write. Whether the app *runs*
that way is a preview trial, not a unit test.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = (ROOT / "deploy/compose.app.yml").read_text()
DOCKERFILE = (ROOT / "Dockerfile").read_text()

MIB = {"m": 1, "g": 1024}


def _mib(value: str) -> int:
    match = re.fullmatch(r"(\d+)([mg])", value.strip().strip('"'))
    assert match, f"{value!r} is not a size in m or g"
    return int(match.group(1)) * MIB[match.group(2)]


def _setting(key: str) -> str:
    found = re.search(rf"^    {key}:\s*(.+)$", COMPOSE, re.M)
    assert found, f"compose sets no {key}"
    return found.group(1).split("#")[0].strip()


def test_the_image_is_read_only_and_tmp_is_memory() -> None:
    """The image is code. What the app writes goes to the volume or to /tmp,
    and a compromised process cannot rewrite the code it runs."""
    assert _setting("read_only") == "true"
    tmp = re.search(r'^    tmpfs:\s*\n\s+-\s*"?/tmp:([^"\n]+)', COMPOSE, re.M)
    assert tmp, "/tmp must be a tmpfs once the root is read-only"
    size = re.search(r"size=(\d+[mg])", tmp.group(1))
    assert size and _mib(size.group(1)) >= 128, "`backup verify` unpacks a whole copy into /tmp"


def test_every_capability_is_dropped_and_none_can_be_regained() -> None:
    """Port 4000 is above 1024 and the app runs as `nina`: it needs none."""
    assert re.search(r"^    cap_drop:\s*\[\s*ALL\s*\]", COMPOSE, re.M)
    assert re.search(r'^\s+-\s*"?no-new-privileges:true"?', COMPOSE, re.M)


def test_memory_and_processes_are_bounded_with_room_above_what_was_measured() -> None:
    memory = _mib(_setting("mem_limit"))
    assert memory >= 4 * 223, "four times the measured peak, at least"
    assert _mib(_setting("memswap_limit")) == memory, "no swap beyond the limit"
    assert 64 <= int(_setting("pids_limit")) <= 4096


def test_cpu_is_shared_rather_than_capped() -> None:
    """A hard `cpus` quota throttles even on an idle host. A lower weight yields
    to the neighbours when there is contention and uses both cores when not."""
    assert "cpus:" not in COMPOSE
    assert 0 < int(_setting("cpu_shares")) < 1024


def test_the_app_runs_as_nobody_special() -> None:
    users = re.findall(r"^USER\s+(\S+)", DOCKERFILE, re.M)
    assert users and users[-1] not in ("root", "0"), "the last USER is who runs the app"


def test_everything_the_app_writes_is_on_the_volume() -> None:
    """With the root read-only, a path configured outside /data is a crash
    waiting for its first write."""
    for key in ("NINANATUR_DB", "NINANATUR_CACHE_DIR"):
        configured = re.search(rf"{key}=(\S+)", DOCKERFILE)
        assert configured and configured.group(1).startswith("/data/"), key
    assert re.search(r"NINANATUR_DB:\s*/data/", COMPOSE)
