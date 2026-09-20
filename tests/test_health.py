"""Is every source still there — Wave 25.

No network: the portals are functions here. What is checked is that the checker
catches the four ways a source has actually broken while this registry was
built — a moved host, a renamed coverage, a stale row answered with HTML and a
200, and an archive that no longer holds the tile it held.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from ninanatur.geo.health import Verdict, check_coverage, check_tile_source, looks_like
from ninanatur.geo.terrain_sources import TERRAIN_SOURCES
from ninanatur.geo.tile_grid import TileProduct
from ninanatur.geo.tile_sources import sources_for

BAYERN = next(s for s in sources_for("BY") if s.product is TileProduct.DGM1)
RHEINLAND = next(s for s in sources_for("RP") if s.product is TileProduct.DGM1)
SAARLAND = next(s for s in sources_for("SL") if s.product is TileProduct.DGM1)
NRW_SERVICE = next(s for s in TERRAIN_SOURCES if s.state == "Nordrhein-Westfalen")

METALINK = (Path(__file__).parent / "fixtures" / "rp_dgm1_metalink.meta4").read_bytes()
A_TIFF = b"II*\x00" + b"\x00" * 4_000
AN_APOLOGY = (b"<!DOCTYPE html><html><body>Folgender Datensatz konnte nicht "
              b"heruntergeladen werden. Die verwendete Massendownload-Datei ist "
              b"veraltet.</body></html>")


def _portal(body: bytes = A_TIFF, *, size: int | None = None):
    """A state's file host, as three functions."""
    def get(url: str) -> bytes:
        return METALINK if url.endswith(".meta4") else body

    def ranged(url: str, start: int, end: int) -> bytes:
        return get(url)[start:end + 1]

    def sized(url: str) -> int:
        return size if size is not None else len(get(url))

    return {"get": get, "sized": sized, "ranged": ranged}


def test_bytes_that_are_what_they_claim() -> None:
    assert looks_like(A_TIFF, "GeoTIFF") is None
    assert looks_like(b"LASF\x00\x00", "LAZ") is None
    assert looks_like(b"PK\x03\x04junk", "zip") is None


def test_an_apology_served_with_a_200_is_named_as_one() -> None:
    """Schleswig-Holstein answers a stale row this way, and a checker that
    looked at the status code would call it healthy."""
    assert looks_like(AN_APOLOGY, "GeoTIFF") == "an HTML page"


def test_a_source_serving_the_wrong_format_is_named_as_that() -> None:
    assert looks_like(b"PK\x03\x04", "GeoTIFF") == "zip"


def test_a_healthy_tile_source_passes_and_says_what_it_saw() -> None:
    check = check_tile_source(BAYERN, **_portal(size=BAYERN.probed_bytes))
    assert check.verdict is Verdict.OK
    assert not check.wrong
    assert "690_5334" in check.detail
    assert "GeoTIFF" in check.detail


def test_a_host_that_has_stopped_answering_is_gone() -> None:
    """Bayern's laser moved host while this registry was being written, and
    every old path answers 404."""
    def missing(url: str) -> bytes:
        raise OSError("404 Not Found")

    check = check_tile_source(BAYERN, get=missing, sized=missing, ranged=missing)
    assert check.verdict is Verdict.GONE
    assert "690_5334" in check.detail


def test_a_portal_answering_html_with_a_200_is_changed_not_ok() -> None:
    check = check_tile_source(BAYERN, **_portal(AN_APOLOGY))
    assert check.verdict is Verdict.CHANGED
    assert "an HTML page" in check.detail


def test_a_tile_that_has_become_a_different_size_of_thing_is_changed() -> None:
    """A new flight over the same ground changes a tile's size by a half; a
    hundredfold is a different product wearing the same name."""
    check = check_tile_source(BAYERN, **_portal(size=BAYERN.probed_bytes * 100))
    assert check.verdict is Verdict.CHANGED
    assert "when probed" in check.detail


def test_a_new_flight_over_the_same_ground_is_not_an_alarm() -> None:
    check = check_tile_source(BAYERN, **_portal(size=int(BAYERN.probed_bytes * 1.6)))
    assert check.verdict is Verdict.OK


def test_a_source_found_through_a_list_reads_the_list() -> None:
    """Rheinland-Pfalz writes a flight year into the name, so the list is the
    only route — and reading it is most of what there is to check."""
    asked: list[str] = []
    portal = _portal()
    original = portal["get"]

    def watched(url: str) -> bytes:
        asked.append(url)
        return original(url)

    check = check_tile_source(RHEINLAND, get=watched, sized=portal["sized"],
                              ranged=portal["ranged"])
    assert check.verdict is Verdict.OK
    assert any(url.endswith(".meta4") for url in asked)
    assert "dgm1_32_337_5553_1_rp_2025.tif" in check.detail


def test_a_list_that_has_stopped_listing_is_gone() -> None:
    def empty(url: str) -> bytes:
        return b'<?xml version="1.0"?><metalink xmlns="urn:ietf:params:xml:ns:metalink"/>'

    check = check_tile_source(RHEINLAND, get=empty, sized=lambda _u: 0,
                              ranged=lambda _u, _s, _e: b"")
    assert check.verdict is Verdict.GONE


def test_an_archive_passes_on_its_own_directory() -> None:
    """Saarland publishes no tile. Its archive's directory still holding the
    square kilometre is the whole question, and costs three requests."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("DGM1_tif_NK/dgm1_32_348_5475_1_SL_2025.tif", A_TIFF)
    body = out.getvalue()

    check = check_tile_source(
        SAARLAND, get=lambda _u: body, sized=lambda _u: len(body),
        ranged=lambda _u, start, end: body[start:end + 1])
    assert check.verdict is Verdict.OK
    assert "dgm1_32_348_5475_1_SL_2025.tif" in check.detail


def test_an_archive_that_no_longer_holds_a_tile_is_gone() -> None:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("readme.txt", b"moved to a new portal")
    body = out.getvalue()

    check = check_tile_source(
        SAARLAND, get=lambda _u: body, sized=lambda _u: len(body),
        ranged=lambda _u, start, end: body[start:end + 1])
    assert check.verdict is Verdict.GONE


def test_a_coverage_service_that_still_names_its_coverage_passes() -> None:
    body = (b'<?xml version="1.0"?><CoverageDescriptions>'
            b"<CoverageId>" + NRW_SERVICE.coverage.encode() + b"</CoverageId>"
            b"</CoverageDescriptions>")
    assert check_coverage(NRW_SERVICE, get=lambda _u: body).verdict is Verdict.OK


def test_a_service_that_has_renamed_its_coverage_is_changed() -> None:
    """The failure worth catching: the service is up, and the one coverage this
    registry asks for is not there any more."""
    body = (b'<?xml version="1.0"?><CoverageDescriptions>'
            b"<CoverageId>nw_dgm_neu_2027</CoverageId></CoverageDescriptions>")
    check = check_coverage(NRW_SERVICE, get=lambda _u: body)
    assert check.verdict is Verdict.CHANGED
    assert "no longer names" in check.detail


def test_a_service_behind_a_security_gate_is_changed() -> None:
    """The federal DGM1 answers NOACCESS_SERVICE from a gate, which is a 200."""
    body = (b"<ows:ExceptionReport><ows:Exception>NOACCESS_SERVICE"
            b"</ows:Exception></ows:ExceptionReport>")
    assert check_coverage(NRW_SERVICE, get=lambda _u: body).verdict is Verdict.CHANGED


@pytest.mark.parametrize("source", [BAYERN, RHEINLAND, SAARLAND])
def test_every_kind_of_address_can_be_checked_at_all(source: object) -> None:
    """Computed, listed and archived: the checker must know all three, or a
    whole class of source silently goes unwatched."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("DGM1_tif_NK/dgm1_32_348_5475_1_SL_2025.tif", A_TIFF)
    body = out.getvalue()

    def get(url: str) -> bytes:
        return METALINK if url.endswith(".meta4") else (body if url.endswith(".zip") else A_TIFF)

    def sized(url: str) -> int:
        # An archive must report its real length or its directory cannot be
        # found; a plain tile reports whatever the registry recorded, so size
        # drift is not what is under test here.
        if url.endswith(".zip"):
            return len(get(url))
        return source.probed_bytes or len(get(url))  # type: ignore[attr-defined]

    check = check_tile_source(source, get=get, sized=sized,  # type: ignore[arg-type]
                              ranged=lambda u, s, e: get(u)[s:e + 1])
    assert check.verdict is Verdict.OK, check.detail


def test_a_host_that_answers_but_will_not_say_how_much_is_still_there() -> None:
    """Bayern's laser host serves no range and states no length, so neither
    looking inside nor measuring works. It answered, which is the question —
    and the report says plainly that nothing was read."""
    def silent(url: str) -> None:
        return None

    def no_ranges(url: str, start: int, end: int) -> bytes:
        raise OSError("this host ignores Range")

    def too_big(url: str) -> bytes:
        raise OSError("112 MB is not a health check")

    check = check_tile_source(BAYERN, get=too_big, sized=lambda _u: 0,
                              ranged=no_ranges, present=silent)
    assert check.verdict is Verdict.OK
    assert "not sampled" in check.detail
    assert "size not stated" in check.detail


def test_a_host_that_answers_nothing_at_all_is_still_gone() -> None:
    """The distinction that matters: silent is not the same as absent."""
    def refused(url: str) -> None:
        raise OSError("404 Not Found")

    def no_ranges(url: str, start: int, end: int) -> bytes:
        raise OSError("404 Not Found")

    check = check_tile_source(BAYERN, get=refused, sized=lambda _u: 0,  # type: ignore[arg-type]
                              ranged=no_ranges, present=refused)
    assert check.verdict is Verdict.GONE


def test_a_text_grid_is_recognised_by_being_numbers() -> None:
    """XYZ has no magic bytes — it is numbers, one line per cell. Bremen puts
    an `x y z` header above its first row, so the second line has to count."""
    assert looks_like(b"424000.50 6002999.50 1.05\r\n424001.50 6002999.50 1.06\r\n",
                      "XYZ") is None
    assert looks_like(b"x y z\n465000 5896999 1.4\n", "XYZ") is None
    assert looks_like(b"-9.50 6002999.50 1.05\n", "XYZ") is None


def test_an_apology_is_still_an_apology_where_a_grid_was_expected() -> None:
    """The case this whole checker exists for, and a text format must not be
    the hole in it."""
    assert looks_like(AN_APOLOGY, "XYZ") == "an HTML page"
    assert looks_like(b"Die Datei ist veraltet.\nBitte neu laden.\n", "XYZ") == "no numbers"
