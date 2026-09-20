"""A tile that arrives in an archive — Wave 25, feature 1 (doc 103).

No network: the archives are built here. What is checked is what the six
zipping states actually do — one wanted member beside sidecars, a second
extension for the same thing, and a member that lies about its size.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from geokachel.tile_zip import (
    MAX_MEMBER_BYTES,
    ArchiveError,
    extract,
    unpack,
)


def _zip(*members: tuple[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, body in members:
            archive.writestr(name, body)
    return out.getvalue()


def test_the_one_member_that_is_the_tile() -> None:
    """Thüringen wraps a GeoTIFF with an .xyz of the same heights and a .meta;
    Sachsen adds a world file and a CSV. One of them is the tile."""
    archive = _zip(
        ("dgm1_32_561_5609_1_th_2020-2025.tif", b"II*\x00pixels"),
        ("dgm1_32_561_5609_1_th_2020-2025.xyz", b"561000.5 5609000.5 214.77\n"),
        ("dgm1_32_561_5609_1_th_2020-2025.meta", b"Genauigkeit Hoehe: 0.15-0.30m"),
    )
    assert unpack(archive, want=(".tif",)) == [b"II*\x00pixels"]


def test_the_same_thing_under_two_extensions() -> None:
    """CityGML is `.gml` in most states and `.xml` in Berlin and Schleswig-
    Holstein. It is the same format, so it is one entry with two spellings."""
    berlin = _zip(("LoD2_33_372_5808_1_BE.xml", b"<CityModel/>"))
    thuringia = _zip(("LoD2_32_598_5696_2_TH.gml", b"<CityModel/>"),
                     ("LoD2_32_598_5696_2_TH.txt", b"Stand: 2025"))
    for archive in (berlin, thuringia):
        assert unpack(archive, want=(".gml", ".xml")) == [b"<CityModel/>"]


def test_extensions_are_matched_whatever_their_case() -> None:
    """A state that ships `.TIF` is shipping a tile, not a surprise."""
    assert unpack(_zip(("DGM1_33278_5590.TIF", b"II*\x00")), want=(".tif",)) == [b"II*\x00"]


def test_several_wanted_members_come_back_in_name_order() -> None:
    """Baden-Württemberg's 2 km archive holds four 1 km tiles. Name order is
    the grid's order, so the caller can pair them with their corners."""
    archive = _zip(
        ("LoD2_32_514_5405_1_BW.gml", b"d"), ("LoD2_32_513_5404_1_BW.gml", b"a"),
        ("LoD2_32_514_5404_1_BW.gml", b"c"), ("LoD2_32_513_5405_1_BW.gml", b"b"),
    )
    assert unpack(archive, want=(".gml",)) == [b"a", b"b", b"c", b"d"]


def test_a_folder_inside_the_archive_is_not_a_tile() -> None:
    """Hamburg and Bremen nest their tiles in directories, and a directory
    entry ends in the separator and has no bytes."""
    archive = _zip(("s32_466/dom1_32_466_5973_1_hh_2022.tif", b"II*\x00"))
    assert unpack(archive, want=(".tif",)) == [b"II*\x00"]


def test_nothing_of_the_wanted_kind_is_an_error_and_says_so() -> None:
    """A state that changes what it packs should be told about at once, not
    read as a tile with no ground in it."""
    with pytest.raises(ArchiveError, match="no .tif"):
        unpack(_zip(("readme.txt", b"hello")), want=(".tif",))


def test_something_that_is_not_an_archive_is_refused_tidily() -> None:
    """A portal that answers a maintenance page with 200 — which Schleswig-
    Holstein does — must not surface as a zipfile traceback."""
    with pytest.raises(ArchiveError):
        unpack(b"<!DOCTYPE html><html>Wartungsarbeiten</html>", want=(".tif",))


def test_a_member_that_claims_to_be_enormous_is_refused_before_it_is_read() -> None:
    """The header is the only thing trusted before allocating: a declared size
    past the cap is refused while it is still a declaration (Wave 20)."""
    archive = _zip(("dgm1.tif", b"\x00" * 64))
    with pytest.raises(ArchiveError, match="too large"):
        unpack(archive, want=(".tif",), max_member_bytes=32)


def test_the_cap_is_big_enough_for_the_products_it_guards() -> None:
    """Thüringen's CityGML is 36 MB of XML uncompressed and its laser member
    about 110 MB. A cap that refuses the data it guards guards nothing."""
    assert MAX_MEMBER_BYTES >= 150_000_000


def test_the_member_is_written_out_beside_its_archive(tmp_path: Path) -> None:
    """Thüringen, Sachsen and Brandenburg zip their point clouds, and the
    reader streams from a file rather than from bytes (doc 107). So the member
    is copied out once and read from there."""
    archive = tmp_path / "las_32_561_5609_1_th_2020-2025.zip"
    archive.write_bytes(_zip(("las_32_561_5609_1_th_2020-2025.laz", b"LASF points"),
                             ("las_32_561_5609_1_th_2020-2025.xml", b"<meta/>")))
    out = extract(archive, want=(".laz", ".las"), out=tmp_path / "th" / "tile.laz")
    assert out.read_bytes() == b"LASF points"
    assert not list(tmp_path.rglob("*.part")), "a half-written tile must not survive"


def test_a_member_already_written_out_is_not_written_again(tmp_path: Path) -> None:
    """A second garden on the same street reads the file that is already
    there; unpacking a hundred megabytes again would be the cache's whole
    point undone."""
    archive = tmp_path / "tile.zip"
    archive.write_bytes(_zip(("tile.laz", b"LASF points")))
    out = tmp_path / "tile.laz"
    extract(archive, want=(".laz",), out=out)
    out.write_bytes(b"left alone")
    assert extract(archive, want=(".laz",), out=out).read_bytes() == b"left alone"


def test_an_archive_with_no_cloud_in_it_leaves_nothing_behind(tmp_path: Path) -> None:
    archive = tmp_path / "tile.zip"
    archive.write_bytes(_zip(("readme.txt", b"hello")))
    with pytest.raises(ArchiveError, match="no .laz"):
        extract(archive, want=(".laz",), out=tmp_path / "tile.laz")
    assert not (tmp_path / "tile.laz").exists()
