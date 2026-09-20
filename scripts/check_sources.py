"""Ask every source a garden reads whether it is still there — Wave 25.

    python -m scripts.check_sources             # all of them, a few kB each
    python -m scripts.check_sources sn- rp-     # only names containing these
    python -m scripts.check_sources --quiet     # print only what is wrong

**Exit code 0 when everything answered as the registry says it should, 1 when
anything did not** — so a cron line can mail its output when, and only when,
something has changed:

    17 4 * * 1  cd /srv/ninanatur && .venv/bin/python -m scripts.check_sources
                --quiet || mail -s "NinaNatur: a source moved" you@example.de

This is deliberately **not** part of the test suite (doc 102). A suite that
needs sixteen state surveying offices to be up fails on their maintenance
window, teaches people to ignore red, and tells you nothing about your code.
Run this on a schedule instead, and let it be the thing that goes red.

What it costs: one small request per source, a few kilobytes each, with a
polite pause between. Sixteen offices publishing at their own expense are not
an API with a quota.
"""
from __future__ import annotations

import argparse
import sys
import time

from ninanatur.geo.health import Check, Verdict, check_coverage, check_tile_source
from ninanatur.geo.surface_sources import SURFACE_SOURCES
from ninanatur.geo.terrain_sources import TERRAIN_SOURCES
from ninanatur.geo.tile_entries import TILE_SOURCES
from ninanatur.geo.tile_sources import COPERNICUS_GLO30, glo30_url
from ninanatur.ingest.http import (
    REQUEST_DELAY_S,
    get_bytes,
    get_range,
    presence,
    size_of,
)

#: Generous, and the same reasoning as the probe script's.
POLITE_S = max(REQUEST_DELAY_S, 1.0)

MARK = {Verdict.OK: "ok  ", Verdict.CHANGED: "CHG ", Verdict.GONE: "GONE"}


#: Big enough for the largest list a state publishes — Rheinland-Pfalz's ground
#: metalink is 12 MB and Schleswig-Holstein's GeoJSON 9 — and small enough that
#: a tile served where an index was expected is still refused.
MAX_DOCUMENT = 32_000_000


def _capped(url: str) -> bytes:
    """A whole document, for the hosts that will not serve a range."""
    return get_bytes(url, use_cache=False, max_bytes=MAX_DOCUMENT)


def every_check(only: list[str]) -> list[Check]:
    """Every source, asked once, with a pause between."""
    found: list[Check] = []

    def wanted(name: str) -> bool:
        return not only or any(part.lower() in name.lower() for part in only)

    for source in TILE_SOURCES:
        if not wanted(source.name):
            continue
        found.append(check_tile_source(source, get=_capped, sized=size_of,
                                       ranged=get_range, present=presence))
        _report(found[-1])
        time.sleep(POLITE_S)

    for service, kind in ((TERRAIN_SOURCES, "terrain"), (SURFACE_SOURCES, "surface")):
        for source in service:
            name = f"{kind}: {source.state}"
            if not wanted(name):
                continue
            answered = check_coverage(source, get=_capped)
            found.append(Check(name, answered.verdict, answered.detail))
            _report(found[-1])
            time.sleep(POLITE_S)

    if wanted("copernicus"):
        # The horizon ring for the states that serve nothing, and the only
        # source here that is neither a state nor a tile grid.
        url = glo30_url(48.137, 11.575)
        try:
            head = get_range(url, 0, 3)
            verdict = Verdict.OK if head[:2] in (b"II", b"MM") else Verdict.CHANGED
            detail = f"{COPERNICUS_GLO30.split('/')[2]} — {head!r}"
        except Exception as trouble:  # noqa: BLE001 - the answer is the report
            verdict, detail = Verdict.GONE, f"{type(trouble).__name__}: {trouble}"
        found.append(Check("copernicus-glo30", verdict, detail))
        _report(found[-1])

    return found


_QUIET = False


def _report(check: Check) -> None:
    if _QUIET and not check.wrong:
        return
    print(f"{MARK[check.verdict]} {check.name:16s} {check.detail}")


def main() -> int:
    global _QUIET  # noqa: PLW0603 - a script's one flag
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("only", nargs="*", help="check only sources whose name contains this")
    parser.add_argument("--quiet", action="store_true", help="print only what is wrong")
    chosen = parser.parse_args()
    _QUIET = chosen.quiet

    if not _QUIET:
        print(f"asking each source once, {POLITE_S:.0f}s apart\n")
    checks = every_check(chosen.only)
    wrong = [c for c in checks if c.wrong]

    print(f"\n{len(checks) - len(wrong)} of {len(checks)} answered as the registry says.")
    if wrong:
        print("\nWhat changed:")
        for check in wrong:
            print(f"  {check.name}: {check.detail}")
        print("\nA state may have moved its files, rotated a share token or renamed a "
              "coverage.\nRe-probe it (python -m scripts.probe_tile_sources) and update "
              "the registry\nand its doc — an entry is a request that was answered, and "
              "this one no longer is.")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
