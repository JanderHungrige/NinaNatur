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
HEALTH = ROOT / ".github/workflows/healthz.yml"


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


def test_every_published_port_is_bound_to_the_proxy_interface() -> None:
    """A bare `PORT:4000` binds to 0.0.0.0, and then the app answers the whole
    internet in plaintext, beside the proxy rather than behind it.

    Found on 2026-09-07 and still live on 2026-09-10: `http://<host-ip>:4000`
    and `:4001` both answered, so the TLS, the proxy's exploit rules and the
    forwarded-scheme signal the session cookie relies on were all optional —
    and the preview, which must never be public, was.

    Nginx Proxy Manager runs as a container and reaches the app through the
    Docker bridge gateway, so that is the one interface to bind. Not 127.0.0.1:
    the proxy is not on the host's loopback, and that binding would lock it out.
    """
    ports = re.findall(r'^\s*-\s*"?([^"\n]+:4000)"?\s*$', COMPOSE.read_text(), re.M)
    assert ports, "compose publishes no port at all — the proxy has nothing to reach"
    for port in ports:
        assert port.startswith("172.17.0.1:"), (
            f"{port!r} binds to every interface; bind it to 172.17.0.1"
        )


def test_every_container_log_is_rotated() -> None:
    """Docker's json-file driver keeps everything unless told otherwise, and on
    2026-09-11 nothing on the host told it: every log grew for as long as its
    container lived, holding every address that had ever asked."""
    block = re.search(r"^    logging:\n((?:      .*\n)+)", COMPOSE.read_text(), re.M)
    assert block, "the app service sets no logging options"
    options = block.group(1)
    assert re.search(r"driver:\s*json-file", options)
    size = re.search(r'max-size:\s*"(\d+)([km])"', options)
    files = re.search(r'max-file:\s*"(\d+)"', options)
    assert size and files, "rotation needs both a size and a count"
    assert int(files.group(1)) >= 2


def _probes() -> dict[str, str]:
    """The watch's url → the environment it expects to find there."""
    text = HEALTH.read_text()
    urls = re.findall(r"url:\s*(https://\S+/healthz)", text)
    expected = re.findall(r"expect:\s*(\w+)", text)
    assert urls and len(urls) == len(expected), "every probe needs the environment it expects"
    return dict(zip(urls, expected, strict=True))


def test_both_stacks_are_watched_from_outside() -> None:
    """The preview answered 500 from 2026-09-07 to 2026-09-10 and nobody knew.
    A machine asks now, from outside the host, on a schedule — every name the
    app answers to, expecting the environment its template sets."""
    from ninanatur.web.security import ALLOWED_HOSTS

    # Comment lines may sit between the key and its entry; YAML does not mind.
    assert re.search(r"schedule:\s*\n(?:\s*#.*\n)*\s*-\s*cron:", HEALTH.read_text())
    probes = _probes()
    domains = {h for h in ALLOWED_HOSTS if "." in h and not h.replace(".", "").isdigit()}
    assert {url.split("/")[2] for url in probes} == domains
    assert set(probes.values()) == {env(ENV_PROD)["NINANATUR_ENV"], env(ENV_DEV)["NINANATUR_ENV"]}


def test_the_watch_trusts_no_third_party_action() -> None:
    """Somebody else's code on a schedule is a supply chain of its own; curl and
    python on the runner are all it needs, and they need no pin."""
    assert "uses:" not in HEALTH.read_text()
