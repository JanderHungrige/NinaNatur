"""Compile `requirements-dev.txt`: the tools CI installs beside the image's lock.

    python scripts/compile_dev_lock.py      (needs `uv` on the PATH)

The tools are listed here, in `TOOLS`, and not in a `requirements-dev.in`:
Dependabot pairs a `.txt` with the `.in` of the same name and compiles it
again itself — without the image's lock as a constraint, so every runtime pin
came back into the dev lock, some at other versions (review, 2026-09-22).
Without the `.in` it bumps the dev lock's pins in place, like any hashed
requirements file. A tool update that needs a new dependency cannot be done in
place; run this script for it.

The dev lock used to be the image's lock plus the tools, compiled with
`-c requirements.txt`, so every runtime pin stood in both files. Dependabot
edits `requirements.txt` alone, and every Python proposal failed CI on the
second copy it left behind (2026-09-22). Now each package is pinned in one
file only: this compiles the tools against the image's lock exactly as before,
then leaves out every package the image's lock already pins. CI installs both
files, so it still tests exactly what the image ships, and a proposal that
moves a runtime pin moves the only one there is.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "requirements.txt"
DEV_LOCK = ROOT / "requirements-dev.txt"
PYTHON = "3.13"

#: What CI installs beside the image's lock: the tools, never the app's own
#: dependencies.
TOOLS = (
    "pytest",
    # Refuses every socket that is not a Unix one, so no test can reach the
    # network by accident (`pyproject.toml` addopts; `tests/test_no_network.py`).
    "pytest-socket",
    "ruff",
    "mypy",
    "types-requests",
    "types-defusedxml",
    "httpx",
    "pip-audit",
)

#: A requirement's first line, as uv writes it: `name==version \` or `name[extra]==…`.
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==", re.M)

HEADER = """\
# The tools CI installs beside the image's lock, and nothing the image's lock
# already pins: each package is pinned in one file only, so a Dependabot
# proposal that moves a runtime pin cannot leave a second copy behind. CI
# installs both files (`pip install --require-hashes -r requirements.txt
# -r requirements-dev.txt`). Made by `python scripts/compile_dev_lock.py`,
# which compiles its list of tools against requirements.txt with uv.
"""


def name_of(raw: str) -> str:
    return re.sub(r"[-_.]+", "-", raw).lower()


def pinned(text: str) -> set[str]:
    return {name_of(n) for n in PIN.findall(text)}


def blocks(text: str) -> list[str]:
    """One requirement with its hash and `# via` lines, per entry."""
    return [b for b in re.split(r"\n(?=[A-Za-z0-9])", text) if PIN.match(b)]


def dev_only(compiled: str, image: set[str]) -> str:
    """The compiled dev lock without the packages the image's lock pins."""
    kept = []
    for block in blocks(compiled):
        first = PIN.match(block)
        if first is not None and name_of(first.group(1)) not in image:
            kept.append(block.rstrip("\n"))
    return HEADER + "\n".join(kept) + "\n"


def main() -> int:
    with tempfile.TemporaryDirectory() as scratch:
        tools = Path(scratch) / "tools.in"
        tools.write_text("".join(f"{tool}\n" for tool in TOOLS))
        out = Path(scratch) / "requirements-dev.txt"
        # Seeded with the lock as it stands, so uv keeps every pin it can:
        # compiling afresh moves tools nobody asked to move.
        if DEV_LOCK.exists():
            out.write_text(DEV_LOCK.read_text())
        subprocess.run(
            ["uv", "pip", "compile", "pyproject.toml", str(tools),
             "-c", "requirements.txt", "--universal", "--generate-hashes",
             "--python-version", PYTHON, "--no-header", "-o", str(out)],
            cwd=ROOT, check=True,
        )
        # uv names the list it was given in each `# via` line: the scratch file's
        # path, which differs on every run. Named after where the list lives.
        compiled = out.read_text().replace(f"-r {tools}", "TOOLS in scripts/compile_dev_lock.py")
        DEV_LOCK.write_text(dev_only(compiled, pinned(LOCK.read_text())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
