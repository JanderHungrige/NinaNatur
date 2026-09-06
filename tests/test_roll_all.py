"""The cron does both environments, in order, and stops when one fails.

Shell, so it is tested by running it against a stand-in for `auto-deploy.sh`
rather than by reading it. The bug this replaces — two crontab lines racing one
lock — was invisible in the file and only visible in the behaviour, which is the
argument for testing the behaviour.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def host(tmp_path: Path) -> Path:
    """A pretend /opt/ninanatur with a recording stand-in for auto-deploy.sh."""
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    shutil.copy(ROOT / "deploy/roll-all.sh", deploy / "roll-all.sh")
    (deploy / "auto-deploy.sh").write_text(
        '#!/usr/bin/env bash\n'
        'echo "$1" >> "$(dirname "$0")/rolled.txt"\n'
        '[ -z "${FAIL_ON:-}" ] || case "$1" in *"$FAIL_ON"*) exit 1;; esac\n'
    )
    os.chmod(deploy / "auto-deploy.sh", 0o755)
    return tmp_path


def run(host: Path, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(host / "deploy/roll-all.sh")],
        capture_output=True, text=True, env={**os.environ, **env}, check=False,
    )


def rolled(host: Path) -> list[str]:
    log = host / "deploy/rolled.txt"
    return log.read_text().split() if log.exists() else []


def test_it_rolls_nothing_that_is_not_configured(host: Path) -> None:
    """The normal state of a host running only production: no .env.dev, no
    complaint, no attempt."""
    assert run(host).returncode == 0
    assert rolled(host) == []


def test_production_goes_first(host: Path) -> None:
    """Not alphabetical, not the order somebody typed. Production matters most
    and is rolled before anything else touches the registry."""
    (host / "deploy/.env.dev").write_text("APP_PORT=4001\n")
    (host / "deploy/.env.prod").write_text("APP_PORT=4000\n")

    assert run(host).returncode == 0
    assert rolled(host) == ["deploy/.env.prod", "deploy/.env.dev"]


def test_a_failed_production_roll_stops_the_rest(host: Path) -> None:
    """If production could not be rolled the reason is usually the registry or
    the daemon, and trying dev against the same broken thing only fills the log."""
    (host / "deploy/.env.prod").write_text("x\n")
    (host / "deploy/.env.dev").write_text("x\n")

    result = run(host, FAIL_ON="prod")

    assert result.returncode == 1
    assert rolled(host) == ["deploy/.env.prod"], "dev was tried anyway"
    assert "stopping" in result.stderr


def test_adding_dev_later_needs_no_reinstall(host: Path) -> None:
    """The crontab line does not name the environments. A host that gains a
    .env.dev starts rolling it on the next tick."""
    (host / "deploy/.env.prod").write_text("x\n")
    run(host)
    assert rolled(host) == ["deploy/.env.prod"]

    (host / "deploy/.env.dev").write_text("x\n")
    run(host)

    assert rolled(host)[-2:] == ["deploy/.env.prod", "deploy/.env.dev"]


def test_the_crontab_installs_exactly_one_line_for_this_project() -> None:
    """The defect this feature exists to fix: two lines, both with the same
    sleep, racing one lock. One line cannot race itself."""
    installer = (ROOT / "deploy/install-cron.sh").read_text()
    emitted = [
        line for line in installer.splitlines()
        if line.strip().startswith('echo "* * * * *')
    ]
    assert len(emitted) == 1, f"{len(emitted)} cron lines would be installed"
    assert "roll-all.sh" in emitted[0]
    assert "auto-deploy.sh" not in emitted[0], "the cron calls the loop, not one env"
