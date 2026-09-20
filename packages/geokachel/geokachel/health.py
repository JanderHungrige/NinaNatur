"""Is every source a garden reads still there — Wave 25.

Doc 102's rule is that the probe is not a test: a suite needing sixteen state
portals to be up fails on their maintenance window. This is the other half of
the same rule — the thing run **deliberately**, by hand or on a schedule, to
find out that a state moved its files before a gardener does.

**A status code is not an answer**, and every one of these was met while the
registry was being built:

- Niedersachsen's own index still lists LoD2 tiles whose paths now 404.
- Schleswig-Holstein answers a stale row with **HTTP 200 and an HTML apology**.
- Sachsen's download page carries two share tokens that no longer work, while
  its viewer's configuration carries the working set.
- Bayern's laser moved host entirely; every old path answers 404.

So a source passes only when what comes back **is what it claims to be**: a
TIFF that begins `II*`, a CityGML with a root element, a LAZ whose header says
`LASF`, an archive whose directory still holds the square kilometre it held
before. Cheap by default — a few kilobytes off the front of each — because
sixteen surveying offices are public infrastructure nobody is paying us to
hammer, and a weekly check that downloads a gigabyte is a check that gets
turned off.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from geokachel.remote_zip import Ranged, Sized, names_in
from geokachel.tile_grid import TileSource, corner_in

#: Enough of a file to say what it is, and little enough to ask for often.
SAMPLE_BYTES = 4096

#: A size this far from what the probe recorded is a different product rather
#: than a new flight over the same ground. Rheinland-Pfalz's tiles vary by half
#: between flight years, so three times is generous on purpose.
SIZE_DRIFT = 3.0

#: A text grid announces itself only by being numbers. Bremen writes an
#: `x y z` header above its first row, so a letter at the front is not proof
#: of trouble — but an HTML apology still is, and that is what this catches.
NUMERIC = b"0123456789-+."

#: How each format announces itself in its first bytes.
MAGIC: dict[str, tuple[bytes, ...]] = {
    "GeoTIFF": (b"II*\x00", b"MM\x00*"),
    "LAZ": (b"LASF",),
    "CityGML": (b"<?xml", b"<Cit", b"\xef\xbb\xbf<?xml", b"<core", b"<!--"),
    "zip": (b"PK\x03\x04", b"PK\x05\x06"),
}

Get = Callable[[str], bytes]


class Coverage(Protocol):
    """What the terrain and surface registries have in common: a service, and
    the one coverage inside it that is asked for by name.

    Read-only on purpose: the registries are frozen dataclasses, and a protocol
    that declared these as settable would not match one.
    """

    @property
    def state(self) -> str: ...

    @property
    def url(self) -> str: ...

    @property
    def coverage(self) -> str: ...


class Verdict(StrEnum):
    """What a source had to say for itself."""

    #: It answered, with what it claims to be.
    OK = "ok"
    #: It answered with something else — a different format, or a size that is
    #: not a new flight over the same ground.
    CHANGED = "changed"
    #: It did not answer at all.
    GONE = "gone"


@dataclass(frozen=True)
class Check:
    """One source, asked."""

    name: str
    verdict: Verdict
    detail: str

    @property
    def wrong(self) -> bool:
        return self.verdict is not Verdict.OK


@dataclass(frozen=True)
class Target:
    """The one thing worth asking a source for: a tile it should still hold."""

    describe: str
    #: Fetchable directly, where the address is one. None for a member of an
    #: archive, whose directory has already answered the question.
    url: str | None
    declared_bytes: int | None


def looks_like(sample: bytes, want: str) -> str | None:
    """None when the bytes are what they claim, else what they look like.

    An HTML apology served with a 200 is the case this exists for.
    """
    if any(sample.startswith(magic) for magic in MAGIC.get(want, ())):
        return None
    head = sample[:64].lstrip()
    # Named before anything else, because an apology served with a 200 is the
    # case this exists for and it must not be reported as merely the wrong kind.
    if head[:9].lower() in (b"<!doctype", b"<html>"[:9]) or head[:5].lower() == b"<html":
        return "an HTML page"
    if want == "XYZ":
        # No magic bytes: a grid is numbers, one line per cell. Bremen's header
        # line means the first token may be a word, so the second line decides.
        rows = sample.split(b"\n", 2)
        starts = [row.lstrip()[:1] for row in rows[:2]]
        return None if any(c and c in NUMERIC for c in starts) else "no numbers"
    for name, magics in MAGIC.items():
        if any(sample.startswith(magic) for magic in magics):
            return name
    return f"bytes beginning {sample[:8]!r}"


def _sample(url: str, *, ranged: Ranged, get: Get) -> bytes | None:
    """The front of a file, by range where the host allows one, else None.

    Sachsen refuses a HEAD and Schleswig-Holstein ignores a Range; both still
    answer a plain GET, so a host that will not be sampled is asked outright.
    But Bayern's laser ignores a Range *and* is a hundred and twelve megabytes,
    and downloading that to look at four bytes is not a health check. None means
    "could not look inside", which is not the same as "not there".
    """
    try:
        return ranged(url, 0, SAMPLE_BYTES - 1)
    except Exception:  # noqa: BLE001 - a host that will not range is not a fault
        pass
    try:
        return get(url)[:SAMPLE_BYTES]
    except Exception:  # noqa: BLE001 - too large to fetch whole, which is fine
        return None


def target_of(source: TileSource, *, get: Get, sized: Sized, ranged: Ranged) -> Target:
    """A square kilometre this source should still hold, and where it lives.

    A computed source carries the tile the probe actually asked for, so the
    check can compare like with like. A source found through a list or an
    archive needs none: reading the list *is* the check, and whichever tile it
    names first will do.
    """
    if source.archives:
        for url in source.archives:
            for name in names_in(url, size=sized, ranged=ranged):
                leaf = name.rsplit("/", 1)[-1]
                if corner_in(leaf, (0, 0)) != (0, 0):
                    return Target(f"{leaf} in {url.rsplit('/', 1)[-1]}", None, None)
        raise LookupError("every archive is empty of tiles")
    if source.lookup is not None:
        names = source.lookup.parse(get(source.lookup.index_url))
        corner = next(iter(sorted(names)))
        return Target(names[corner], source.lookup.address(names[corner], corner), None)
    if source.probed_tile is None:
        raise LookupError("no tile recorded to ask for")
    east, north = source.probed_tile
    return Target(f"{east}_{north}", source.url_for(east, north), source.probed_bytes)


def check_tile_source(source: TileSource, *, get: Get, sized: Sized, ranged: Ranged,
                      present: Callable[[str], int | None] | None = None) -> Check:
    """Ask one entry whether it is still what the registry says it is.

    `present` answers "does this address answer, and how large does it say it
    is" — None for a host that answers without saying. It is separate from
    `sized`, which an archive's directory reader needs as a real number.
    """
    at_all = present or sized
    try:
        target = target_of(source, get=get, sized=sized, ranged=ranged)
    except Exception as trouble:  # noqa: BLE001 - the answer is the report
        return Check(source.name, Verdict.GONE,
                     f"could not find a tile to ask for: {type(trouble).__name__}: {trouble}")
    if target.url is None:
        # Its archive's own directory answered, which is the whole question for
        # a state that publishes no tile.
        return Check(source.name, Verdict.OK, f"{target.describe} — listed")

    want = "zip" if source.zipped else source.fmt
    sample = _sample(target.url, ranged=ranged, get=get)
    if sample:
        wrong = looks_like(sample, want)
        if wrong is not None:
            return Check(source.name, Verdict.CHANGED,
                         f"{target.describe} — expected {want}, got {wrong}")

    try:
        now = at_all(target.url)
    except Exception as trouble:  # noqa: BLE001 - nothing answered at all
        if sample is None:
            return Check(source.name, Verdict.GONE,
                         f"{target.describe} — {type(trouble).__name__}: {trouble}")
        return Check(source.name, Verdict.OK, f"{target.describe} — {want}, size not stated")

    # A source that states its size is there; one that would not let us look
    # inside is reported as unread rather than as healthy.
    detail = (f"{target.describe} — {want}" if sample
              else f"{target.describe} — not sampled (the host serves no range)")
    if now is None:
        return Check(source.name, Verdict.OK, f"{detail}, size not stated")

    detail = f"{detail}, {now:,} B"
    if target.declared_bytes and not (
            1 / SIZE_DRIFT <= now / target.declared_bytes <= SIZE_DRIFT):
        return Check(source.name, Verdict.CHANGED,
                     f"{detail} against {target.declared_bytes:,} B when probed")
    return Check(source.name, Verdict.OK, detail)


def check_coverage(source: Coverage, *, get: Get) -> Check:
    """Ask a coverage service whether it still serves the coverage we name.

    `DescribeCoverage` rather than `GetCapabilities`: a service can be up and
    have renamed or dropped the one coverage this registry asks for, and that
    is the failure worth catching.
    """
    url = (f"{source.url}?SERVICE=WCS&VERSION=2.0.1&REQUEST=DescribeCoverage"
           f"&COVERAGEID={source.coverage}")
    name = f"{source.state} ({source.coverage})"
    try:
        body = get(url)[:8192]
    except Exception as trouble:  # noqa: BLE001
        return Check(name, Verdict.GONE, f"{type(trouble).__name__}: {trouble}")
    if b"ExceptionReport" in body or b"NOACCESS" in body:
        return Check(name, Verdict.CHANGED, "the service answered with an exception")
    # As a whole token, not a substring: a service that renamed `nw_dgm` to
    # `nw_dgm_neu_2027` still contains the old name, and would pass.
    if not re.search(rb"\b" + re.escape(source.coverage.encode()) + rb"\b", body):
        return Check(name, Verdict.CHANGED, "the service no longer names this coverage")
    return Check(name, Verdict.OK, "describes its coverage")


__all__ = [
    "MAGIC",
    "Coverage",
    "SAMPLE_BYTES",
    "SIZE_DRIFT",
    "Check",
    "Target",
    "Verdict",
    "check_coverage",
    "check_tile_source",
    "looks_like",
    "target_of",
]
