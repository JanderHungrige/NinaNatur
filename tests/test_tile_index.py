"""Reading a state's list of what it has — Wave 25, feature 1 (doc 103).

Checked against Rheinland-Pfalz's own metalink rather than against a document
written here to its own expectations: `tests/fixtures/rp_dgm1_metalink.meta4`
is the head of the real 12 MB file, fetched on 2026-09-20.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ninanatur.geo.tile_index import MAX_INDEX_BYTES, ListingError, from_metalink

RP = Path(__file__).parent / "fixtures" / "rp_dgm1_metalink.meta4"


def test_the_states_own_list_reads_as_a_grid() -> None:
    """The point of the whole exercise: 419/5490 was flown in 2022 and
    337/5553 in 2025, and no arithmetic gets you from one name to the other."""
    listed = from_metalink(RP.read_bytes())
    assert listed[(419, 5490)] == "dgm1_32_419_5490_1_rp_2022.tif"
    assert listed[(337, 5553)] == "dgm1_32_337_5553_1_rp_2025.tif"
    assert listed[(420, 5566)] == "dgm1_32_420_5566_1_rp_2024.tif"
    assert len(listed) == 4


def test_the_url_in_the_list_is_not_read_at_all() -> None:
    """An index is remote content. A state's list that began answering with
    somebody else's address must change nothing — what is taken from it is a
    file name, and the folder it goes into is the registry's own."""
    forged = RP.read_bytes().replace(
        b"<url>https://geobasis-rlp.de/data/dgm1/current/tif/dgm1_32_419_5490_1_rp_2022.tif</url>",
        b"<url>https://example.invalid/whatever.tif</url>")
    assert from_metalink(forged)[(419, 5490)] == "dgm1_32_419_5490_1_rp_2022.tif"


@pytest.mark.parametrize("forged", [
    b'name="../../../etc/passwd"',
    b'name="/etc/passwd"',
    b'name="https://example.invalid/x.tif"',
    b'name="dgm1 32 419 5490.tif"',
])
def test_a_name_that_is_not_a_file_name_is_dropped(forged: bytes) -> None:
    """Not repaired, dropped. A state does not publish a tile called
    `../../etc/passwd`, so one appearing is not a tile that needs fixing."""
    listed = from_metalink(RP.read_bytes().replace(
        b'name="dgm1_32_419_5490_1_rp_2022.tif"', forged))
    assert (419, 5490) not in listed
    assert len(listed) == 3, "the other three are still tiles"


def test_a_name_with_no_grid_in_it_is_not_a_tile() -> None:
    """Some states put a readme or a licence in the same list."""
    listed = from_metalink(RP.read_bytes().replace(
        b'name="dgm1_32_419_5490_1_rp_2022.tif"', b'name="Nutzungsbedingungen.pdf"'))
    assert len(listed) == 3


def test_something_that_is_not_a_list_is_refused_tidily() -> None:
    with pytest.raises(ListingError):
        from_metalink(b"<!DOCTYPE html><html>Wartungsarbeiten</html>")


def test_a_list_with_no_tiles_in_it_is_refused_rather_than_read_as_empty() -> None:
    """An empty answer read as "this state has nothing" would quietly take the
    ground away from every garden in it."""
    with pytest.raises(ListingError, match="no tile"):
        from_metalink(b'<?xml version="1.0"?><metalink '
                      b'xmlns="urn:ietf:params:xml:ns:metalink"></metalink>')


def test_a_document_far_larger_than_a_list_of_names_is_refused() -> None:
    """Twelve megabytes is Rheinland-Pfalz's ground. A hundred and twenty is
    not a longer list, it is a different kind of document."""
    with pytest.raises(ListingError, match="not a list of names"):
        from_metalink(b"<metalink/>" + b" " * MAX_INDEX_BYTES)
