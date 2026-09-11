"""Keep what worked, and go back to it — Wave 20, feature 7, part 2.

Until 2026-09-11 `auto-deploy.sh` pulled the tag, recreated the container and
then pruned dangling images — which, once the tag had moved, included the image
it had just replaced: the one thing it could have gone back to. Nothing waited
for the health check. A build that started and then failed it stayed live until
somebody noticed, with nothing local to roll back to.

Shell, so it is tested by running it against a stand-in for `docker`
(`tests/fake_docker.py`) that records what it was asked to do — the approach
`test_roll_all.py` takes with a stand-in for this very script.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REPO = "ghcr.io/o/ninanatur"
A, B, C = ("sha256:" + ch * 64 for ch in "abc")


@pytest.fixture()
def host(tmp_path: Path) -> Path:
    """A pretend /opt/ninanatur with a production env file, and a PATH whose
    `docker` is the stand-in."""
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    shutil.copy(ROOT / "deploy/auto-deploy.sh", deploy / "auto-deploy.sh")
    (deploy / ".env.prod").write_text("IMAGE_TAG=main\nAPP_PORT=4000\n")
    tools = tmp_path / "bin"
    tools.mkdir()
    (tools / "docker").write_text(
        f'#!/bin/sh\nexec "{sys.executable}" "{ROOT / "tests/fake_docker.py"}" "$@"\n')
    (tools / "flock").write_text("#!/bin/sh\nexit 0\n")  # macOS has none; CI's is real
    for tool in tools.iterdir():
        tool.chmod(0o755)
    return tmp_path


def scene(host: Path, *, registry: str, running: str | None,
          health: dict[str, str] | None = None) -> None:
    tags = {f"{REPO}:main": running} if running else {}
    (host / "docker.json").write_text(json.dumps({
        "registry": registry, "running": running, "health": health or {},
        "tags": tags, "calls": [],
    }))


def deploy(host: Path) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PATH": f"{host / 'bin'}:{os.environ['PATH']}",
        "FAKE_DOCKER_STATE": str(host / "docker.json"),
        "HEALTH_WAIT_TRIES": "3",
        "HEALTH_WAIT_SLEEP": "0",
        "NINANATUR_DEPLOY_LOCK": str(host / "deploy.lock"),
    }
    return subprocess.run(
        ["bash", str(host / "deploy/auto-deploy.sh"), "deploy/.env.prod"],
        capture_output=True, text=True, env=env, check=False,
    )


def daemon(host: Path) -> dict[str, object]:
    return dict(json.loads((host / "docker.json").read_text()))


def bad_marker(host: Path) -> str | None:
    marker = host / "deploy/.state/prod.bad"
    return marker.read_text().strip() if marker.exists() else None


# --- the ordinary ticks -------------------------------------------------------------

def test_nothing_new_changes_nothing_but_still_applies_the_compose_file(host: Path) -> None:
    """Most ticks. `up -d` stays, because it is also how a changed compose file —
    last used for log rotation — reaches a running stack."""
    scene(host, registry=A, running=A)
    result = deploy(host)
    assert result.returncode == 0, result.stderr
    assert daemon(host)["calls"] == ["pull main", "up main"]


def test_a_healthy_new_image_stays_and_the_old_one_is_kept_to_go_back_to(host: Path) -> None:
    scene(host, registry=B, running=A, health={B: "healthy"})
    result = deploy(host)
    assert result.returncode == 0, result.stderr
    assert daemon(host)["calls"] == [
        "pull main", f"tag {A} {REPO}:main-previous", "up main", "prune",
    ]
    assert daemon(host)["running"] == B
    assert f"@{B}" in result.stdout, "say which build is live, by digest"


# --- a build that fails its health check -----------------------------------------------

def test_an_unhealthy_new_image_is_rolled_back_and_nothing_is_pruned(host: Path) -> None:
    scene(host, registry=B, running=A, health={B: "unhealthy", A: "healthy"})
    result = deploy(host)
    assert result.returncode == 1
    assert daemon(host)["calls"] == [
        "pull main", f"tag {A} {REPO}:main-previous", "up main", "up main-previous",
    ]
    assert daemon(host)["running"] == A
    assert bad_marker(host) == B
    assert "rolling back" in result.stdout + result.stderr


def test_a_build_that_failed_here_is_not_tried_again_every_minute(host: Path) -> None:
    """Otherwise the next tick rolls it forward again, and production flaps
    between a broken build and a working one once a minute."""
    scene(host, registry=B, running=A, health={B: "unhealthy", A: "healthy"})
    deploy(host)
    calls_before = len(daemon(host)["calls"])  # type: ignore[arg-type]

    result = deploy(host)

    assert result.returncode == 0, result.stderr
    assert daemon(host)["calls"][calls_before:] == ["pull main", "up main-previous"]  # type: ignore[index]
    assert daemon(host)["running"] == A


def test_a_newer_build_after_a_bad_one_is_tried(host: Path) -> None:
    scene(host, registry=B, running=A, health={B: "unhealthy", A: "healthy", C: "healthy"})
    deploy(host)
    state = daemon(host)
    state["registry"] = C
    (host / "docker.json").write_text(json.dumps(state))

    result = deploy(host)

    assert result.returncode == 0, result.stderr
    assert daemon(host)["running"] == C
    assert bad_marker(host) is None


def test_a_first_deploy_has_nothing_to_go_back_to_and_says_so(host: Path) -> None:
    scene(host, registry=B, running=None, health={B: "unhealthy"})
    result = deploy(host)
    assert result.returncode == 1
    assert daemon(host)["calls"] == ["pull main", "up main"]
    assert bad_marker(host) == B


def test_the_deploy_state_is_never_committed() -> None:
    """It names the build that failed on this host; it belongs to the host."""
    ignored = (ROOT / ".gitignore").read_text().splitlines()
    assert "deploy/.state/" in ignored
