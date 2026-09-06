"""The deploy files have to agree with each other, and nothing else checks that.

Four files encode one arrangement: the workflow decides which branch produces
which image tag, the env templates decide which tag each stack pulls and on
which port, and the compose file wires them together. They are edited at
different times for different reasons, and a disagreement between them does not
fail — it deploys the wrong image, or nothing at all, silently.

Asserting self-consistency rather than fixed values, per CLAUDE.md: the test
should survive somebody renaming the tag and fail if they rename it in one place
only.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github/workflows/deploy.yml"
COMPOSE = ROOT / "deploy/compose.app.yml"
ENV_PROD = ROOT / "deploy/.env.prod.example"
ENV_DEV = ROOT / "deploy/.env.dev.example"


def env(path: Path) -> dict[str, str]:
    """The settings from a `.env` template, comments and blanks dropped."""
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def test_the_workflow_builds_from_both_branches() -> None:
    """A stack pulling a tag nothing builds sits on whatever it started with,
    for as long as nobody looks."""
    text = WORKFLOW.read_text()
    branches = re.search(r"branches:\s*\[([^\]]+)\]", text)
    assert branches is not None
    named = {b.strip() for b in branches.group(1).split(",")}
    assert named == {"main", "dev-deployment"}


def test_every_tag_a_stack_pulls_is_a_tag_the_workflow_pushes() -> None:
    """The join between CI and the host, which nothing else expresses."""
    text = WORKFLOW.read_text()
    built = set(re.findall(r'echo "tag=(\w+)" >> "\$GITHUB_OUTPUT"', text))
    assert built, "the workflow no longer names its tags in a readable way"

    for template in (ENV_PROD, ENV_DEV):
        tag = env(template)["IMAGE_TAG"]
        assert tag in built, f"{template.name} pulls :{tag}, which CI does not build"


def test_the_two_stacks_differ_in_everything_that_keeps_them_apart() -> None:
    """Project name, port and tag. Sharing any one of them means the preview and
    the live site are the same thing wearing two names — and sharing the project
    name means sharing the volume, which is testing a migration against real
    gardens."""
    prod, dev = env(ENV_PROD), env(ENV_DEV)
    for key in ("COMPOSE_PROJECT_NAME", "APP_PORT", "IMAGE_TAG", "NINANATUR_ENV"):
        assert prod[key] != dev[key], f"prod and dev share {key}={prod[key]}"


def test_the_stacks_agree_on_everything_that_must_be_the_same() -> None:
    """The registry, the owner and the image name. A preview built from another
    repository would look right and prove nothing."""
    prod, dev = env(ENV_PROD), env(ENV_DEV)
    for key in ("REGISTRY", "OWNER", "IMAGE"):
        assert prod[key] == dev[key], f"prod and dev disagree on {key}"


def test_compose_reads_every_variable_the_templates_set() -> None:
    """A template setting something compose never reads is a setting somebody
    believes is doing work."""
    text = COMPOSE.read_text()
    used = set(re.findall(r"\$\{(\w+)", text))
    # COMPOSE_PROJECT_NAME is read by the compose tool itself rather than by the
    # file, which is exactly why it is easy to think it is unused and remove it.
    used.add("COMPOSE_PROJECT_NAME")
    for template in (ENV_PROD, ENV_DEV):
        for key in env(template):
            assert key in used, f"{template.name} sets {key}, which compose ignores"


@pytest.mark.parametrize("template", [ENV_PROD, ENV_DEV])
def test_a_template_carries_no_real_secret(template: Path) -> None:
    """The templates are tracked and the real files are not. A token pasted into
    the example is a token in the repository."""
    token = env(template).get("NINANATUR_GITHUB_TOKEN", "")
    assert token == "", f"{template.name} carries a token value"
