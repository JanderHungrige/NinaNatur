"""The version shown in the header: `V0.5.7`.

Read as major.wave.merges — the product generation, the highest completed MDD
wave, and how many merges have landed on main. It is *derived*, never edited: a
hand-maintained number drifts the moment someone forgets, and this one exists
precisely so the page can be trusted to say what is deployed.

Computed at build time and baked into the image, because the container carries
neither git nor the .mdd directory.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

VERSION_ENV = "NINANATUR_VERSION"
MAJOR = 0
WAVES_DIR = Path(__file__).resolve().parent.parent / ".mdd" / "waves"
UNKNOWN = "dev"


def completed_waves(waves_dir: Path = WAVES_DIR) -> int:
    """The highest wave marked complete. 0 when nothing is."""
    highest = 0
    if not waves_dir.is_dir():
        return highest
    for path in waves_dir.glob("ninanatur-wave-*.md"):
        match = re.search(r"wave-(\d+)\.md$", path.name)
        if match is None:
            continue
        if re.search(r"^status:\s*complete\s*$", path.read_text(), re.M):
            highest = max(highest, int(match.group(1)))
    return highest


def merge_count(repo: Path | None = None) -> int | None:
    """Merges on the current branch, or None outside a git checkout."""
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "--merges", "HEAD"],
            cwd=repo or Path(__file__).resolve().parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return int(value) if value.isdigit() else None


def compute_version() -> str | None:
    """Derive the version here and now. None when git is unavailable."""
    merges = merge_count()
    if merges is None:
        return None
    return f"V{MAJOR}.{completed_waves()}.{merges}"


def app_version() -> str:
    """What the app reports.

    The baked-in value wins: inside the container there is no git history to
    count and no .mdd to read, so a computed fallback there would be wrong rather
    than merely missing.
    """
    baked = os.environ.get(VERSION_ENV, "").strip()
    if baked:
        return baked
    return compute_version() or UNKNOWN
