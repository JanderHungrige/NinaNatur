"""Locked and signed — Wave 20, feature 7, part 1: the chain around the code.

Found on 2026-09-11 before this: `pyproject.toml` named only lower bounds and
there was no lockfile, so CI tested whatever PyPI served that minute and the
image, built in a separate job, installed whatever it served a minute later —
"what was tested" and "what was shipped" were two resolutions that merely
usually agreed. No dependency was audited. Every GitHub Action and both base
images were referenced by a tag their owners can move. Dependabot was off. And
`.dockerignore` excluded no `.env` file — the frontend stage copies its whole
directory, and Vite bakes `VITE_*` variables from a `.env` into the public bundle.

Self-consistency, per CLAUDE.md: these assert that the files agree with each
other, not that any version is a particular number.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "requirements.txt"
DEV_LOCK = ROOT / "requirements-dev.txt"
DOCKERFILE = ROOT / "Dockerfile"
WORKFLOWS = sorted((ROOT / ".github/workflows").glob("*.yml"))
DEPLOY = ROOT / ".github/workflows/deploy.yml"
DEPENDABOT = ROOT / ".github/dependabot.yml"
DOCKERIGNORE = ROOT / ".dockerignore"

PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s;\\]+)", re.M)


def _name(raw: str) -> str:
    return re.sub(r"[-_.]+", "-", raw).lower()


def _pins(path: Path) -> dict[str, str]:
    return {_name(name): version for name, version in PIN.findall(path.read_text())}


def _blocks(path: Path) -> list[str]:
    """One requirement with its continuation lines, per entry."""
    return [b for b in re.split(r"\n(?=[A-Za-z0-9])", path.read_text()) if PIN.match(b)]


# --- the lock ---------------------------------------------------------------------------

def test_the_lock_pins_every_declared_dependency() -> None:
    declared = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    pinned = _pins(LOCK)
    for requirement in declared:
        name = _name(re.split(r"[\[<>=!~ ;]", requirement, maxsplit=1)[0])
        assert name in pinned, f"{name} is declared but not locked"


def test_every_locked_line_carries_its_hashes() -> None:
    """A pin without a hash is a name, not a lock: the index could serve anything
    under it. `--require-hashes` refuses the whole install if one is missing."""
    for path in (LOCK, DEV_LOCK):
        blocks = _blocks(path)
        assert blocks, f"{path.name} locks nothing"
        for block in blocks:
            assert "--hash=sha256:" in block, f"{path.name}: {block.splitlines()[0]} has no hash"


def test_ci_tests_exactly_what_the_image_ships() -> None:
    """The finding itself: two resolutions that merely usually agreed."""
    shipped, tested = _pins(LOCK), _pins(DEV_LOCK)
    for name, version in shipped.items():
        assert tested.get(name) == version, (
            f"the image ships {name}=={version}, CI tests {tested.get(name)}"
        )


def test_the_lock_is_for_the_python_the_image_runs() -> None:
    command = re.search(r"uv pip compile .*--python-version (\d+\.\d+)", LOCK.read_text())
    image = re.search(r"^FROM python:(\d+\.\d+)-slim", DOCKERFILE.read_text(), re.M)
    assert command and image, "the lock no longer says how it was made"
    assert command.group(1) == image.group(1)


def test_the_image_installs_the_hashed_lock_and_nothing_else() -> None:
    text = DOCKERFILE.read_text()
    assert "--require-hashes -r requirements.txt" in text
    assert "--no-deps ." in text, "the project itself must not pull its own dependencies"
    assert '"uvicorn[standard]" fastapi' not in text, "an unpinned install beside the lock"


def test_ci_installs_the_hashed_dev_lock() -> None:
    text = DEPLOY.read_text()
    assert "pip install --require-hashes -r requirements-dev.txt" in text
    assert "pip install --no-deps -e ." in text
    assert "pip install -e . pytest" not in text


# --- the audits -------------------------------------------------------------------------

def test_ci_audits_what_ships() -> None:
    """The shipped Python and the shipped bundle. The frontend's dev tooling is
    audited too, but not gated: it never reaches a visitor (plan item D2)."""
    text = DEPLOY.read_text()
    assert re.search(r"pip-audit\b.*-r requirements\.txt", text)
    assert "npm audit --omit=dev" in text


# --- nothing anybody can move ---------------------------------------------------------

def test_every_action_is_pinned_to_a_commit() -> None:
    """A tag is a pointer its owner can move — or anybody who takes over the
    owner's account. A commit hash is what was reviewed."""
    for workflow in WORKFLOWS:
        for line in workflow.read_text().splitlines():
            used = re.search(r"uses:\s*([^\s#]+)", line)
            if used is None:
                continue
            assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", used.group(1)), (
                f"{workflow.name}: {used.group(1)} is not pinned to a commit"
            )
            assert re.search(r"#\s*v\d", line), f"{workflow.name}: say which version the pin is"


def test_every_base_image_is_pinned_by_digest() -> None:
    for image in re.findall(r"^FROM\s+(\S+)", DOCKERFILE.read_text(), re.M):
        assert re.search(r"@sha256:[0-9a-f]{64}$", image), f"{image} is a tag, not a digest"


def test_dependabot_watches_everything_pinned_and_proposes_through_the_preview() -> None:
    """Pins that nothing updates rot. Every ecosystem pinned above, with the
    preview branch as the target, so an update is looked at before it is live."""
    text = DEPENDABOT.read_text()
    for ecosystem, directory in (("pip", "/"), ("npm", "/frontend"),
                                 ("github-actions", "/"), ("docker", "/")):
        entry = re.search(
            rf'package-ecosystem:\s*"?{re.escape(ecosystem)}"?\s*\n\s*directory:\s*"?'
            rf'{re.escape(directory)}"?', text)
        assert entry, f"dependabot does not watch {ecosystem} in {directory}"
    targets = re.findall(r'target-branch:\s*"?([\w-]+)"?', text)
    assert targets and set(targets) == {"dev-deployment"}


def test_a_dependency_update_is_tested_before_anybody_merges_it() -> None:
    """Dependabot opens pull requests, and the workflow ran only on pushes — its
    proposals would have arrived untested."""
    text = DEPLOY.read_text()
    assert re.search(r"^  pull_request:", text, re.M)
    assert "if: github.event_name != 'pull_request'" in text, (
        "a pull request must never push an image"
    )


# --- what the image may contain -------------------------------------------------------

def test_no_env_file_can_reach_an_image() -> None:
    lines = [line.strip() for line in DOCKERIGNORE.read_text().splitlines()]
    for pattern in ("**/.env", "**/.env.*", "frontend/node_modules"):
        assert pattern in lines, f".dockerignore does not exclude {pattern}"
    # The shipped catalogue lives under an excluded directory and is let back in.
    assert lines.index("!ninanatur/data/catalogue.sqlite") > lines.index("data")


def test_a_pull_request_builds_the_image_but_never_pushes_it() -> None:
    """Dependabot's base-image and action bumps change the Dockerfile and the
    build job — and a pull request skipped that job entirely, so they passed on
    the test job alone. A pull request builds now; only a push publishes."""
    text = DEPLOY.read_text()
    job = text[text.index("  build-and-push:"):]
    assert "pull_request" not in job[: job.index("steps:")], "the whole job is skipped for a PR"
    steps = re.split(r"\n      - ", job)
    login = next(s for s in steps if "docker/login-action" in s)
    push = next(s for s in steps if "docker push" in s)
    build = next(s for s in steps if "docker build" in s)
    assert "if: github.event_name != 'pull_request'" in login
    assert "if: github.event_name != 'pull_request'" in push
    assert "if:" not in build.split("run:")[0], "the build itself runs for every event"
    assert "docker push" not in build, "building and publishing are separate steps"


def test_dependabot_proposes_new_digests_not_a_new_interpreter() -> None:
    """A new Python in the base image needs a lock made for it; the lock test
    turns such a proposal red, and it would stay red. Digests and patches only —
    a new Python or Node is a deliberate change, made with its lock."""
    text = DEPENDABOT.read_text()
    docker = text[text.index('package-ecosystem: "docker"'):]
    assert "version-update:semver-major" in docker
    assert "version-update:semver-minor" in docker
