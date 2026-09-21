"""The committed API schema is the one the backend generates, wherever it runs.

CI's check that the generated types are in sync never compared anything: it
ran `git diff -- frontend/…` from inside `frontend/`, and a pathspec that
matches no file is a diff with nothing in it (found 2026-09-21). Making it
compare exposed that the document itself depended on where it was generated:
it carried the app's version, whose last number is the count of merges, and a
development-only page appeared in it wherever no bundle had been built.

These assert self-consistency, the project's rule for tests that must not
depend on their environment: what is committed agrees with what the backend
says now, and nothing in it comes from the machine it was made on.
"""
import json
import re
from pathlib import Path

from scripts.generate_openapi import OUTPUT, VERSION, document, render

WORKFLOW = Path(".github/workflows/deploy.yml")


def test_the_committed_schema_is_what_the_backend_generates() -> None:
    """Stale types are caught here, before a push, as well as in CI."""
    assert OUTPUT.read_text(encoding="utf-8") == render(), (
        "frontend/openapi.json is stale — run `npm run generate:api` in frontend/"
    )


def test_the_schema_carries_no_version_from_the_git_history() -> None:
    info = document()["info"]
    assert isinstance(info, dict)
    assert info["version"] == VERSION
    committed = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert not re.fullmatch(r"V\d+\.\d+\.\d+", committed["info"]["version"])


def test_the_development_page_is_not_part_of_the_contract() -> None:
    """It is served only where no bundle was built: CI builds none, a laptop
    usually has one, and the two generated different documents."""
    paths = document()["paths"]
    assert isinstance(paths, dict)
    assert "/" not in paths
    assert all(path.startswith(("/api/", "/healthz")) for path in paths)


def test_the_workflow_compares_from_the_repository_root() -> None:
    """A bare `cd` in the step moves the `git diff` that follows it."""
    text = WORKFLOW.read_text(encoding="utf-8")
    start = text.index("name: API types are in sync with the backend")
    step = text[start : text.index("\n  build-and-push:", start)]
    commands = [line.strip() for line in step.splitlines() if line.strip() and
                not line.strip().startswith("#")]
    assert any(c.startswith("git diff --exit-code -- frontend/openapi.json") for c in commands)
    assert not any(c.startswith("cd ") for c in commands), "the diff would run in frontend/"
