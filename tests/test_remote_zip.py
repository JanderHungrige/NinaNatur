"""One tile out of an archive that is never fetched — Wave 25, feature 1.

No network: a real zip is built here and served through a range function that
counts what was asked for. What is checked is the property the whole technique
exists for — that a tile costs a fraction of its archive.
"""
from __future__ import annotations

import io
import random
import zipfile

import pytest
from geokachel.remote_zip import RemoteArchiveError, member_of, names_in


class Portal:
    """A state's file host, serving ranges and keeping the bill."""

    def __init__(self, body: bytes) -> None:
        self.body = body
        self.requests = 0
        self.served = 0

    def size(self, _url: str) -> int:
        return len(self.body)

    def ranged(self, _url: str, start: int, end: int) -> bytes:
        chunk = self.body[start:end + 1]
        self.requests += 1
        self.served += len(chunk)
        return chunk


def _tile(index: int, each: int) -> bytes:
    """Bytes that do not compress, so the archive is the size a real one is.
    A tile of identical bytes would deflate to nothing and the directory would
    look like most of the file, which is the opposite of the case under test."""
    return b"II*\x00" + random.Random(index).randbytes(each)


def _archive(members: int = 300, each: int = 40_000) -> bytes:
    """An archive shaped like Saarland's: a few hundred tiles in one file."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zipped:
        for index in range(members):
            east, north = 348 + index % 20, 5475 + index // 20
            zipped.writestr(f"DGM1_tif_NK/dgm1_32_{east}_{north}_1_SL_2025.tif",
                            _tile(index, each))
    return out.getvalue()


def test_the_archives_own_directory_is_the_index() -> None:
    """Saarland publishes no tile and no list of tiles. It does not need to:
    the archive says what is in it, and the directory is at the end."""
    portal = Portal(_archive())
    found = names_in("https://portal/dgm1.zip", size=portal.size, ranged=portal.ranged)
    assert len(found) == 300
    assert found[0] == "DGM1_tif_NK/dgm1_32_348_5475_1_SL_2025.tif"
    assert portal.served < len(portal.body) // 20, "a directory is not the archive"


def test_one_tile_costs_a_fraction_of_its_archive() -> None:
    """The measurement the technique stands on: 0.38 % of Saarland's 559 MB
    for one tile, on 2026-09-20. A test cannot assert a network figure, so it
    asserts the shape of it — what is served is the member, not the file."""
    portal = Portal(_archive())
    wanted = "DGM1_tif_NK/dgm1_32_358_5482_1_SL_2025.tif"
    body = member_of("https://portal/dgm1.zip", wanted,
                     size=portal.size, ranged=portal.ranged)
    assert body.startswith(b"II*\x00")
    assert len(body) == 40_004
    assert portal.served < len(portal.body) // 10, (
        f"served {portal.served} of {len(portal.body)}")
    assert portal.requests < 20


def test_a_member_that_is_not_there_says_so() -> None:
    portal = Portal(_archive(members=4))
    with pytest.raises(RemoteArchiveError, match="not in"):
        member_of("https://portal/dgm1.zip", "dgm1_32_999_9999_1_SL_2025.tif",
                  size=portal.size, ranged=portal.ranged)


def test_a_member_larger_than_the_cap_is_refused_before_it_is_read() -> None:
    """Measured from the directory, so the refusal costs nothing."""
    portal = Portal(_archive(members=2, each=50_000))
    before = portal.served
    with pytest.raises(RemoteArchiveError, match="too large"):
        member_of("https://portal/dgm1.zip", "DGM1_tif_NK/dgm1_32_348_5475_1_SL_2025.tif",
                  size=portal.size, ranged=portal.ranged, max_bytes=1_000)
    assert portal.served - before < 50_000, "the refusal must not read the member"


def test_something_that_is_not_an_archive_is_refused_tidily() -> None:
    portal = Portal(b"<!DOCTYPE html><html>Wartungsarbeiten</html>" * 100)
    with pytest.raises(RemoteArchiveError):
        names_in("https://portal/dgm1.zip", size=portal.size, ranged=portal.ranged)


def test_an_empty_answer_is_not_an_empty_archive() -> None:
    portal = Portal(b"")
    with pytest.raises(RemoteArchiveError, match="0 bytes"):
        names_in("https://portal/dgm1.zip", size=portal.size, ranged=portal.ranged)
