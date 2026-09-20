"""Where a tile's name is not the grid — Wave 25, feature 1 (doc 103).

Most states name a tile after two kilometre numbers and nothing else, which is
why the registry can compute an address. Two do not: Rheinland-Pfalz and
Schleswig-Holstein write the **flight year** into the name
(`dgm1_32_419_5490_1_rp_2022.tif`), and a flight year is not arithmetic — the
tile next door was flown in 2025. Both publish a list of every tile they hold,
so the name is read from there, once.

**An index is remote content, and it is read as data rather than as an
address.** What is taken from it is a *file name*: matched against a strict
character set, and kept only if it carries the grid it claims. The scheme, the
host and the folder stay the registry's own, so a state's index that began
answering with somebody else's URL would change nothing about where this
fetches from. Doc 102's guarantee — every address is a template and two
integers — survives with one word added: and a name the state gave us.
"""
from __future__ import annotations

import json
import logging
import re
from urllib.parse import parse_qs, urlparse

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring

from geokachel.tile_grid import corner_in

log = logging.getLogger(__name__)

#: A file name and nothing else: no separator, no parent, no scheme, no space.
#: A name that does not match is not repaired, it is dropped — a state does not
#: publish a tile called `../../etc/passwd`, so one appearing is not a tile.
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")

#: An index is big — twelve megabytes for Rheinland-Pfalz's ground — but it is
#: still a list of names. Ten times that is a different kind of document.
MAX_INDEX_BYTES = 120_000_000


class ListingError(ValueError):
    """A listing this will not read."""


def from_metalink(data: bytes) -> dict[tuple[int, int], str]:
    """Every tile a metalink4 index lists, by the grid corner in its name.

    Metalink gives each file a name, a size, a sha-256 and one or more URLs.
    Only the name is taken. Where two entries claim the same square kilometre —
    a state re-flying a tile without dropping the old row — the later one wins,
    which is the same "most recent survey" rule the rest of the registry keeps.
    """
    if len(data) > MAX_INDEX_BYTES:
        raise ListingError(f"index is {len(data)} bytes, which is not a list of names")
    try:
        root = fromstring(data)
    except (DefusedXmlException, SyntaxError, ValueError) as broken:
        raise ListingError(f"not a metalink this can read: {broken}") from broken
    found: dict[tuple[int, int], str] = {}
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "file":
            continue
        name = (element.get("name") or "").strip()
        if not SAFE_NAME.match(name):
            continue
        corner = corner_in(name, (0, 0))
        if corner != (0, 0):
            found[corner] = name
    if not found:
        raise ListingError("a metalink with no tile in it")
    return found


def from_geojson_links(data: bytes) -> dict[tuple[int, int], str]:
    """Every tile a Schleswig-Holstein download index lists, by grid corner.

    The same job as `from_metalink` against a different document. Each feature
    carries `kachel` — the zone, the easting and the northing run together as
    `32<EEE><NNNN>` — and a ready-made download URL under `link_data`, or
    `data_link` for the building model, because the two were written by
    different people.

    **Only the file name is taken out of that URL**, and only if it is a file
    name: the address is rebuilt from the registry's own template (doc 103).
    The state's list can therefore change which tile is fetched and never which
    host is asked.
    """
    if len(data) > MAX_INDEX_BYTES:
        raise ListingError(f"index is {len(data)} bytes, which is not a list of names")
    try:
        document = json.loads(data)
        features = document["features"]
    except (ValueError, TypeError, KeyError) as broken:
        raise ListingError(f"not an index this can read: {broken}") from broken

    found: dict[tuple[int, int], str] = {}
    for feature in features:
        held = feature.get("properties") if isinstance(feature, dict) else None
        if not isinstance(held, dict):
            continue
        link = held.get("link_data") or held.get("data_link") or ""
        name = parse_qs(urlparse(str(link)).query).get("file", [""])[0].strip()
        if not SAFE_NAME.match(name):
            continue
        corner = corner_in(name, (0, 0))
        if corner != (0, 0):
            found[corner] = name
    if not found:
        raise ListingError("an index with no tile in it")
    return found


__all__ = [
    "MAX_INDEX_BYTES",
    "SAFE_NAME",
    "ListingError",
    "from_geojson_links",
    "from_metalink",
]
