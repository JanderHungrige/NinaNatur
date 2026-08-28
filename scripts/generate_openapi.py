"""Dump the FastAPI OpenAPI schema for the TypeScript generator.

Run via `npm run generate:api`, which then feeds this into openapi-typescript.
Kept as a script rather than a live fetch so the generation needs no running
server and works in CI.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ninanatur.web.app import app

OUTPUT = Path("frontend/openapi.json")


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    OUTPUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    routes = len(schema.get("paths", {}))
    print(f"wrote {OUTPUT} ({routes} paths)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
