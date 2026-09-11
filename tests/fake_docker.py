#!/usr/bin/env python3
"""A stand-in for `docker`, for `tests/test_auto_deploy.py`.

A small registry and daemon kept in the JSON file `FAKE_DOCKER_STATE` names:
which image id each local tag points at, what the registry hands out on a pull,
which image the stack's one container runs, and how healthy each image turns out
to be once it runs. Every call that changes something is recorded, so a test can
assert what the deploy script *did* rather than what it printed.

Only the calls `deploy/auto-deploy.sh` makes are understood; anything else fails
loudly, so a new call in the script cannot pass the tests by accident.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

REPO = "ghcr.io/o/ninanatur"


def _tag(args: list[str]) -> str:
    """IMAGE_TAG as compose would interpolate it: the shell wins over the file."""
    if os.environ.get("IMAGE_TAG"):
        return os.environ["IMAGE_TAG"]
    with open(args[args.index("--env-file") + 1]) as env_file:
        for line in env_file:
            if line.startswith("IMAGE_TAG="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("fake docker: the env file names no IMAGE_TAG")


def _compose(state: dict[str, Any], args: list[str]) -> None:
    tag = _tag(args)
    verb = args[args.index("-f") + 2]
    if verb == "config":
        print(f"{REPO}:{tag}")
    elif verb == "pull":
        state["tags"][f"{REPO}:{tag}"] = state["registry"]
        state["calls"].append(f"pull {tag}")
    elif verb == "ps":
        print("cid" if state.get("running") else "")
    elif verb == "up":
        state["running"] = state["tags"][f"{REPO}:{tag}"]
        state["calls"].append(f"up {tag}")
    else:
        raise SystemExit(f"fake docker: unexpected compose call {args}")


def _format(args: list[str]) -> str:
    return args[args.index("--format") + 1]


def main(args: list[str]) -> None:
    with open(os.environ["FAKE_DOCKER_STATE"]) as handle:
        state: dict[str, Any] = json.load(handle)
    if args[0] == "compose":
        _compose(state, args)
    elif args[:2] == ["image", "inspect"]:
        image = state["tags"][args[-1]]
        print(image if _format(args) == "{{.Id}}" else f"{REPO}@{image}")
    elif args[:2] == ["image", "prune"]:
        state["calls"].append("prune")
    elif args[0] == "inspect":
        running = state["running"]
        print(running if _format(args) == "{{.Image}}" else state["health"].get(running, "healthy"))
    elif args[0] == "tag":
        state["tags"][args[2]] = state["tags"].get(args[1], args[1])
        state["calls"].append(f"tag {args[1]} {args[2]}")
    else:
        raise SystemExit(f"fake docker: unexpected call {args}")
    with open(os.environ["FAKE_DOCKER_STATE"], "w") as handle:
        json.dump(state, handle)


if __name__ == "__main__":
    main(sys.argv[1:])
