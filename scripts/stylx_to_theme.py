"""Warren Davison's Draft Sketch style in, the plan's Draft Sketch theme out (doc 97).

    python -m scripts.stylx_to_theme            regenerate the theme from the fetched file
    python -m scripts.stylx_to_theme --check    regenerate elsewhere, compare byte for byte
    python -m scripts.stylx_to_theme --fetch    download the pinned file first

The file is his: ArcGIS Online item 3215e720…, "Draft Sketch" by WarrenDz. It
is used and adapted with his written permission (THIRD_PARTY.md), pinned by
size and SHA-256 in assets/draft-sketch/source.json, and never committed —
only what is derived from it is, and --check proves it is derived.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from scripts.draft_sketch import cim, emit
from scripts.draft_sketch.layers import layers_of
from scripts.draft_sketch.lines import line_overlays_of
from scripts.draft_sketch.outline import Overlay, overlays_of
from scripts.draft_sketch.tiles import Images, pattern_of

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "draft-sketch" / "source.json"
STYLX = ROOT / "assets" / "draft-sketch" / "Draft_Sketch.stylx"
OUT = ROOT / "frontend" / "src" / "themes" / "draft-sketch" / "generated"

#: The symbols the theme draws with — ours on the left, his on the right. Which
#: of our kinds gets which is the theme's (themes/draft-sketch/index.ts).
CHOSEN: dict[str, str] = {
    "building-near": "Buildings (LOD 1)",
    "building-mid": "Building (LOD 2)",
    "building-far": "Building (LOD 3)",
    "tree-near": "Tree 1 (LOD 1)",
    "tree-mid": "Tree 1 (LOD 2)",
    "tree-far": "Tree 1 (LOD 3)",
    "shrub-near": "Tree 2 (LOD 1)",
    "shrub-mid": "Tree 2 (LOD 2)",
    "shrub-far": "Tree 2 (LOD 3)",
    "grass": "Grass",
    "water": "Water (area)",
    "sand": "Sand",
    "brick": "Interlock Brick Grid",
    "grey": "Gray Fill",
    "brown": "Brown Fill",
    "green": "Dark Green Fill",
    "dashed": "Dashed Outline",
}
#: His line symbols, laid along a fence's or a wall's line (doc 98).
LINES: dict[str, str] = {
    "wood-fence": "Wood Fence",
    "brick-wall": "Brick Wall",
}


class PinMismatch(Exception):
    """The file is not the one source.json pins."""


def verified(path: Path, pin: dict[str, Any]) -> Path:
    """The file, if it is the pinned one — nothing is read from it otherwise."""
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != pin["bytes"] or digest != pin["sha256"]:
        raise PinMismatch(
            f"{path.name} is {len(data)} bytes, sha256 {digest[:12]}…; "
            f"the pin is {pin['bytes']} bytes, sha256 {pin['sha256'][:12]}…")
    return path


def fetch(pin: dict[str, Any], dest: Path) -> Path:
    """Download the pinned file — only when asked to, and kept only if it matches."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with (tempfile.NamedTemporaryFile(dir=dest.parent, delete=False, suffix=".part") as part,
          urllib.request.urlopen(pin["url"], timeout=120) as response):
        while chunk := response.read(1 << 16):
            part.write(chunk)
    partial = Path(part.name)
    try:
        verified(partial, pin)
    except PinMismatch:
        partial.unlink()
        raise
    return partial.replace(dest)


def generate(stylx: Path, out: Path) -> None:
    """Write the theme's generated half into `out`, replacing what was there."""
    pin = json.loads(SOURCE.read_text())
    verified(stylx, pin)
    symbols = cim.read_symbols(stylx, CHOSEN.values())
    images = Images()
    patterns: list[emit.Pattern] = []
    ramps: list[emit.Gradient] = []
    masks: set[str] = set()
    overlays: dict[str, list[Overlay]] = {}
    for name, title in CHOSEN.items():
        layers = layers_of(symbols[title])
        symbol_id = f"ds-{name}"
        pattern = pattern_of(symbol_id, layers, images)
        if pattern is not None:
            patterns.append(pattern)
        overlays[symbol_id], washes, marks = overlays_of(symbol_id, layers, images)
        ramps += washes
        masks |= marks
    lines = cim.read_symbols(stylx, LINES.values(), symbol_class=4)
    for name, title in LINES.items():
        overlays[f"ds-{name}"], marks = line_overlays_of(f"ds-{name}", layers_of(lines[title]),
                                                         images)
        masks |= marks
    for old in [*out.glob("images/*.png"), *out.glob("*.ts")]:
        old.unlink()
    (out / "images").mkdir(parents=True, exist_ok=True)
    for key, data in images.files.items():
        (out / "images" / f"{key}.png").write_bytes(data)
    paths = {key: f"images/{key}.png" for key in images.files}
    (out / "symbols.ts").write_text(
        emit.symbols_file(patterns, ramps, paths, pin["sha256"], masks), encoding="utf-8")
    (out / "rules.ts").write_text(emit.rules_file(overlays, pin["sha256"]), encoding="utf-8")


def _files(folder: Path) -> dict[str, bytes]:
    return {str(p.relative_to(folder)): p.read_bytes() for p in folder.rglob("*") if p.is_file()}


def check(stylx: Path) -> list[str]:
    """What differs between a fresh derivation and what is committed."""
    with tempfile.TemporaryDirectory() as fresh:
        generate(stylx, Path(fresh))
        made, kept = _files(Path(fresh)), _files(OUT)
    return sorted(name for name in made.keys() | kept.keys() if made.get(name) != kept.get(name))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--fetch", action="store_true", help="download the pinned file first")
    parser.add_argument("--check", action="store_true", help="compare, do not write")
    args = parser.parse_args(argv)
    pin = json.loads(SOURCE.read_text())
    if args.fetch:
        fetch(pin, STYLX)
    if not STYLX.exists():
        print(f"{STYLX.relative_to(ROOT)} is not here. It is {pin['url']}\n"
              f"({pin['bytes']} bytes); --fetch downloads it.", file=sys.stderr)
        return 2
    if args.check:
        changed = check(STYLX)
        for name in changed:
            print(f"differs: {name}", file=sys.stderr)
        return 1 if changed else 0
    generate(STYLX, OUT)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
