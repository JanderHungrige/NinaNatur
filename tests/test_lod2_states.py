"""Whose 3D building model this reader can read — Wave 25, feature 3 (doc 105).

Doc 40 built the reader against Nordrhein-Westfalen and the wave's plan assumed
the other states would need adapters of their own: CityGML 2.0 namespaces, a
different roof coding, parts. Bayern does not. This checks that against the
state's own file rather than against a document written here to its own
expectations — one real building, kept in `tests/fixtures`, cut out of the tile
the probe fetched on 2026-09-20.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from ninanatur.garden import building_sync
from ninanatur.garden.roofs import Roof
from ninanatur.geo.lod2 import MAX_TILE_BYTES, buildings_from
from ninanatur.geo.projection import LatLon
from ninanatur.geo.tile_sources import lod2_tiles_for

BAYERN = Path(__file__).parent / "fixtures" / "lod2_bayern_building.gml"
#: The tile the fixture came out of, and the garden it stands over.
MUNICH = LatLon(lat=48.137, lon=11.575)


def test_the_reader_built_for_nrw_reads_bayern_unchanged() -> None:
    """The finding this feature turned on: Bayern publishes CityGML 1.0 with the
    same `bldg:` namespace, `measuredHeight` in metres and AdV roof keys. No
    adapter, only plumbing."""
    found = buildings_from(BAYERN.read_bytes())
    assert len(found) == 1
    building = found[0]
    assert building.building_id == "DEBY_LOD2_59772"
    assert building.roof is Roof.FLAT          # AdV 1000
    assert building.height_m == pytest.approx(11.715)
    # A real outline in UTM32, closed, over Munich.
    assert len(building.outline) > 4
    assert 691_000 < building.outline[0][0] < 692_000
    assert 5_334_000 < building.outline[0][1] < 5_335_000
    # A flat roof's eaves are its height, and it falls nowhere. The eaves are
    # worked out from the roof surfaces and kept to the centimetre; the height
    # is the survey's own number.
    assert building.eaves_m == pytest.approx(11.71)
    assert building.fall_deg is None


def test_a_bavarian_tile_is_larger_than_the_old_cap() -> None:
    """161,627,079 B for one square kilometre of Munich, against Cologne's 38 MB
    (doc 102). The guard was set when NRW was the only state anybody had asked,
    and a guard that refuses the data is a guard that has stopped guarding."""
    assert MAX_TILE_BYTES > 161_627_079


def test_the_state_is_asked_of_the_registry_rather_than_hard_coded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nordrhein-Westfalen used to be an `if` in the sync. Now a state has a
    building model when the registry says it does, and the tile's address comes
    from there too."""
    asked: list[str] = []

    def fetch(url: str, **_kwargs: object) -> bytes:
        asked.append(url)
        return BAYERN.read_bytes()

    monkeypatch.setattr(building_sync, "get_bytes", fetch)
    surveyed = building_sync._surveyed(MUNICH, "Bayern")  # noqa: SLF001 - the unit under test

    assert surveyed is not None and len(surveyed) == 1
    assert asked == ["https://download1.bayernwolke.de/a/lod2/citygml/691_5334.gml"]
    # On the garden's axes, not the survey's: metres from the garden, not UTM.
    assert abs(surveyed[0].outline[0][0]) < 2_000


def test_a_state_with_no_model_in_the_registry_measures_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Not an error and not a guess: the roof shape stays whatever it was."""
    def fetch(url: str, **_kwargs: object) -> bytes:
        raise AssertionError(f"nothing should be fetched for a state with no model: {url}")

    monkeypatch.setattr(building_sync, "get_bytes", fetch)
    assert lod2_tiles_for("Hessen") is None
    assert building_sync._surveyed(MUNICH, "Hessen") is None  # noqa: SLF001


def test_a_zipped_building_tile_is_read_through_its_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Six states wrap the CityGML — with a licence PDF, a currency CSV or an
    HTML metadata page beside it — and Berlin calls it `.xml`. The reader that
    reads Bayern reads what is inside all of them."""
    def fetch(url: str, **_kwargs: object) -> bytes:
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("LoD2_32_598_5696_2_TH.xml", BAYERN.read_bytes())
            archive.writestr("LoD2_32_598_5696_2_TH.txt", b"Stand: 2025-03-01")
        return out.getvalue()

    monkeypatch.setattr(building_sync, "get_bytes", fetch)
    erfurt = LatLon(lat=50.978, lon=11.029)
    surveyed = building_sync._surveyed(erfurt, "Thüringen")  # noqa: SLF001
    assert surveyed is not None and len(surveyed) == 1
    assert surveyed[0].roof is Roof.FLAT


def test_every_kilometre_tile_in_a_two_kilometre_archive_is_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Baden-Württemberg's archive holds four. Reading only the first would
    measure a quarter of the neighbourhood and call it the neighbourhood."""
    def fetch(url: str, **_kwargs: object) -> bytes:
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("LoD2_32_513_5404_2_bw/GOVDATA-Datenlizenz.pdf", b"%PDF-1.4")
            for east in (513, 514):
                for north in (5404, 5405):
                    archive.writestr(
                        f"LoD2_32_513_5404_2_bw/LoD2_32_{east}_{north}_1_BW.gml",
                        BAYERN.read_bytes())
        return out.getvalue()

    monkeypatch.setattr(building_sync, "get_bytes", fetch)
    stuttgart = LatLon(lat=48.7758, lon=9.1829)
    surveyed = building_sync._surveyed(stuttgart, "Baden-Württemberg")  # noqa: SLF001
    assert surveyed is not None and len(surveyed) == 4


def test_the_odd_easting_of_the_south_west_grid_is_respected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Baden-Württemberg's two-kilometre tiles start on an odd easting and an
    even northing: `513_5404` is a tile and `514_5404` is a 404. Flooring to
    the wrong parity asks for a tile that does not exist, every time."""
    asked: list[str] = []

    def fetch(url: str, **_kwargs: object) -> bytes:
        asked.append(url)
        raise AssertionError("not fetched for real")

    monkeypatch.setattr(building_sync, "get_bytes", fetch)
    building_sync._surveyed(LatLon(lat=48.7758, lon=9.1829), "Baden-Württemberg")  # noqa: SLF001
    assert len(asked) == 1
    east, north = (int(part) for part in asked[0].rsplit("/", 1)[-1].split("_")[2:4])
    assert east % 2 == 1, f"an even easting is not a Baden-Württemberg tile: {asked[0]}"
    assert north % 2 == 0
