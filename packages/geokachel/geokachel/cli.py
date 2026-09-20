"""Ask every source whether it is still there.

    geokachel check                 # all of them, a few kB each
    geokachel check sn- rp-         # only names containing these
    geokachel check --quiet         # print only what is wrong
    geokachel sources               # what this registry knows, and whose it is
    geokachel credits BY TH         # the exact credit those states require

**Exit code 0 when everything answered as the registry says, 1 when anything
did not** — so a scheduled job can speak up only when something has changed:

    17 4 * * 1  geokachel check --quiet || mail -s "a source moved" you@example.de

This is deliberately **not** a test suite. A suite that needs sixteen state
surveying offices to be up fails on their maintenance window, teaches people to
ignore red, and says nothing about your code. Run this on a schedule instead,
and let it be the thing that goes red.

What it costs: one small request per source, four kilobytes off the front of
each, with a pause between. Sixteen offices publishing at their own expense are
not an API with a quota — and if you are running this from CI, set
`geokachel.net.USER_AGENT` to something with your own contact in it.
"""
from __future__ import annotations

import argparse
import sys
import time

from geokachel import net
from geokachel.health import Check, Verdict, check_coverage, check_tile_source
from geokachel.surface_sources import SURFACE_SOURCES
from geokachel.terrain_sources import TERRAIN_SOURCES
from geokachel.tile_entries import TILE_SOURCES
from geokachel.tile_sources import COPERNICUS_GLO30, glo30_url

#: Big enough for the largest list a state publishes — Rheinland-Pfalz's ground
#: metalink is 12 MB and Schleswig-Holstein's GeoJSON 9 — and small enough that
#: a tile served where an index was expected is still refused.
MAX_DOCUMENT = 32_000_000

MARK = {Verdict.OK: "ok  ", Verdict.CHANGED: "CHG ", Verdict.GONE: "GONE"}


def _capped(url: str) -> bytes:
    return net.get_bytes(url, max_bytes=MAX_DOCUMENT)


def every_check(only: list[str], *, say: bool = True) -> list[Check]:
    """Every source, asked once, with a pause between."""
    found: list[Check] = []

    def wanted(name: str) -> bool:
        return not only or any(part.lower() in name.lower() for part in only)

    def note(check: Check) -> None:
        found.append(check)
        if say and (check.wrong or not _QUIET):
            print(f"{MARK[check.verdict]} {check.name:16s} {check.detail}", flush=True)

    for source in TILE_SOURCES:
        if wanted(source.name):
            note(check_tile_source(source, get=_capped, sized=net.size_of,
                                   ranged=net.get_range, present=net.presence))
            time.sleep(net.DELAY_S)

    for registry, kind in ((TERRAIN_SOURCES, "terrain"), (SURFACE_SOURCES, "surface")):
        for service in registry:
            name = f"{kind}: {service.state}"
            if wanted(name):
                answered = check_coverage(service, get=_capped)
                note(Check(name, answered.verdict, answered.detail))
                time.sleep(net.DELAY_S)

    if wanted("copernicus"):
        # The worldwide fallback, and the only source here that is neither a
        # state nor a tile grid.
        try:
            head = net.get_range(glo30_url(48.137, 11.575), 0, 3)
            verdict = Verdict.OK if head[:2] in (b"II", b"MM") else Verdict.CHANGED
            detail = f"{COPERNICUS_GLO30.split('/')[2]} — {head!r}"
        except Exception as trouble:  # noqa: BLE001 - the answer is the report
            verdict, detail = Verdict.GONE, f"{type(trouble).__name__}: {trouble}"
        note(Check("copernicus-glo30", verdict, detail))

    return found


_QUIET = False


def _check(chosen: argparse.Namespace) -> int:
    global _QUIET  # noqa: PLW0603 - one flag, one script
    _QUIET = chosen.quiet
    if not _QUIET:
        print(f"asking each source once, {net.DELAY_S:.1f}s apart\n")
    checks = every_check(chosen.only)
    wrong = [c for c in checks if c.wrong]
    print(f"\n{len(checks) - len(wrong)} of {len(checks)} answered as the registry says.")
    if wrong:
        print("\nWhat changed:")
        for check in wrong:
            print(f"  {check.name}: {check.detail}")
        print("\nA state may have moved its files, rotated a share token or renamed a "
              "coverage.\nRe-read it from the source and correct the registry: an entry "
              "is a request\nthat was answered, and this one no longer is.")
    return 1 if wrong else 0


def _sources(chosen: argparse.Namespace) -> int:
    for source in TILE_SOURCES:
        if chosen.only and not any(p.lower() in source.name.lower() for p in chosen.only):
            continue
        fine = (f"{source.cell_m} m" if source.cell_m
                else f"{source.points_per_m2} pts/m²" if source.points_per_m2 else "—")
        print(f"{source.name:12s} {source.state:3s} {source.product.value:5s} "
              f"{source.tile_km} km  {fine:>10s}  {source.licence}")
    return 0


def _credits(chosen: argparse.Namespace) -> int:
    """The exact string each licence requires, for whatever you are showing."""
    seen: set[str] = set()
    for source in TILE_SOURCES:
        if chosen.only and not any(p.lower() in source.state.lower()
                                   or p.lower() in source.name.lower() for p in chosen.only):
            continue
        if source.attribution not in seen:
            seen.add(source.attribution)
            print(f"{source.attribution}  [{source.licence}]")
    if not seen:
        print("no source matched", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="geokachel", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    jobs = parser.add_subparsers(dest="job", required=True)

    asked = jobs.add_parser("check", help="ask every source whether it is still there")
    asked.add_argument("only", nargs="*", help="only sources whose name contains this")
    asked.add_argument("--quiet", action="store_true", help="print only what is wrong")
    asked.set_defaults(run=_check)

    listed = jobs.add_parser("sources", help="what this registry knows")
    listed.add_argument("only", nargs="*")
    listed.set_defaults(run=_sources, quiet=False)

    owed = jobs.add_parser("credits", help="the credit each licence requires")
    owed.add_argument("only", nargs="*")
    owed.set_defaults(run=_credits, quiet=False)

    chosen = parser.parse_args()
    result: int = chosen.run(chosen)
    return result


if __name__ == "__main__":
    sys.exit(main())
