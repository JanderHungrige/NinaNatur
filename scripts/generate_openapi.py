"""Dump the FastAPI OpenAPI schema for the TypeScript generator.

Run via `npm run generate:api` in frontend/, with the project's virtualenv
active; it runs this from the repository root and feeds the result into
openapi-typescript. CI runs the same two steps directly.
Kept as a script rather than a live fetch so the generation needs no running
server and works in CI.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ninanatur.web.app import app

#: Anchored to the repository, not to wherever the script was started from.
OUTPUT = Path(__file__).resolve().parents[1] / "frontend" / "openapi.json"

#: What the committed document says for its version. The app's own version is
#: V<major>.<wave>.<merges>, and the merge count changes with every merge — so a
#: document carrying it was out of date the moment it was committed, and CI's
#: sync check could only ever have passed because it compared nothing (it ran
#: `git diff` from inside `frontend/`, 2026-09-21). The live `/openapi.json`
#: still reports the running version; the contract the types come from has none.
VERSION = "contract"


def document() -> dict[str, object]:
    """The API's schema, the same wherever it is generated.

    Independent of the git history (see VERSION) and of whether a bundle was
    built: the development fallback page at "/" is left out of the schema.
    """
    schema = app.openapi()
    return {**schema, "info": {**schema["info"], "version": VERSION}}


def render() -> str:
    return json.dumps(document(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render())
    paths = document().get("paths")
    routes = len(paths) if isinstance(paths, dict) else 0
    print(f"wrote {OUTPUT} ({routes} paths)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
