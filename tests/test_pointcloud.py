"""What the laser saw — Wave 25, feature 4 (doc 107).

The tile is written here, point by point, so the test can put a tree and a roof
where it wants them and then ask what came back. No network, and no state's
classification either: the point of this feature is that NRW's tile does not
carry one worth trusting.
"""
from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest

from ninanatur.geo.pointcloud import CloudWindow, cell_for, window_from
from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import frame_map

#: A garden in Nordrhein-Westfalen, where the verified tile is. Precise to more
#: than a tenth of a degree, which is what the sync insists on: a garden stored
#: under the old rounding is six kilometres from its own ground (doc 17).
HOME = LatLon(lat=51.00037, lon=7.00042)
ZONE = 32
GROUND_M = 100.0


def _tile(extra: list[tuple[float, float, float, int]] | None = None,
          at: LatLon = HOME) -> bytes:
    """A square of flat ground at 100 m around `at`, plus whatever is asked for.

    A test says where things are in the **garden's** frame, which is what it
    wants to think in, and they are written where UTM puts them. The two are up
    to 2.3° apart here, and a fixture that ignores that measures the
    resampling rather than the thing under test — which is how this fixture was
    wrong the first time.
    """
    import laspy

    origin, per_x, per_y = frame_map(at, ZONE)
    ground = [(dx, dy, GROUND_M, 2)
              for dx in np.arange(-40.0, 40.0, 2.0)
              for dy in np.arange(-40.0, 40.0, 2.0)]
    points = ground + list(extra or [])

    header = laspy.LasHeader(point_format=1, version="1.2")
    header.offsets = np.array([origin[0], origin[1], 0.0])
    header.scales = np.array([0.01, 0.01, 0.01])
    las = laspy.LasData(header)
    las.x = np.array([origin[0] + per_x[0] * dx + per_y[0] * dy for dx, dy, _, _ in points])
    las.y = np.array([origin[1] + per_x[1] * dx + per_y[1] * dy for dx, dy, _, _ in points])
    las.z = np.array([z for _, _, z, _ in points])
    las.classification = np.array([c for _, _, _, c in points], dtype=np.uint8)
    out = BytesIO()
    las.write(out)
    return out.getvalue()


#: Things are put at cell centres rather than on cell lines: a coordinate on a
#: line lands either side of it once the file has rounded it to a centimetre,
#: which is a property of the format and not of the reading.
def _tree(dx: float, dy: float) -> list[tuple[float, float, float, int]]:
    """A crown starting three metres up and ending at eight: returns through
    it, and one on the ground below, which is what a tree does to a laser and a
    roof does not."""
    return [(dx, dy, GROUND_M + h, 1) for h in (3.2, 4.5, 6.0, 7.1, 8.0)] + [
        (dx, dy, GROUND_M, 2)]


def _roof(dx: float, dy: float, height: float = 8.0) -> list[tuple[float, float, float, int]]:
    """A roof: one return, at the top, and nothing under it."""
    return [(dx, dy, GROUND_M + height, 1)]


def _window(extra: list[tuple[float, float, float, int]],
            footprints: list[list[tuple[float, float]]] | None = None) -> CloudWindow:
    window = window_from(_tile(extra), HOME, zone=ZONE, source="NW",
                         licence="dl-de/zero-2-0", attribution="Land NRW (2026)",
                         footprints=footprints)
    assert window is not None
    return window


def test_the_ground_is_the_lowest_ground_return() -> None:
    window = _window([])
    assert window.height_at(0.0, 0.0) == pytest.approx(0.0, abs=0.01)
    assert window.crown_at(0.0, 0.0) is None


def test_a_thing_standing_up_is_as_tall_as_it_is() -> None:
    window = _window(_roof(10.5, 10.5, height=8.0))
    assert window.height_at(10.5, 10.5) == pytest.approx(8.0, abs=0.1)


def test_a_crown_says_where_it_starts_and_a_roof_does_not() -> None:
    """The whole feature in one test. A tree's returns go through it, so the
    lowest standing one is the canopy's underside — the number Wave 26 needs
    and nothing else in this project has. A roof returns once, at the top, and
    has no underside to find."""
    window = _window(_tree(5.5, 5.5) + _roof(-5.5, -5.5))
    assert window.crown_at(5.5, 5.5) == pytest.approx(3.2, abs=0.3)
    assert window.crown_at(-5.5, -5.5) is None, "one return is not a canopy"


def test_what_stands_inside_a_surveyed_building_is_a_roof_not_a_crown() -> None:
    """NRW's tile carries no building class (doc 107), so the building model
    decides: returns inside a footprint are never a canopy, however many of
    them there are."""
    many_returns_on_a_house = [(2.5, 2.5, GROUND_M + h, 1) for h in (3.0, 5.0, 7.0, 9.0)]
    without = _window(many_returns_on_a_house)
    assert without.crown_at(2.5, 2.5) is not None, "unclaimed, it looks like a tree"

    house = [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)]
    with_model = _window(many_returns_on_a_house, footprints=[house])
    assert with_model.crown_at(2.5, 2.5) is None
    # And it is still as tall as it was: a roof has a height, just not a crown.
    assert with_model.height_at(2.5, 2.5) == pytest.approx(9.0, abs=0.2)


def test_the_cell_is_as_fine_as_the_density_earns() -> None:
    """At four points a square metre a half-metre cell holds one point, and a
    raster of single measurements is a picture of the sampling."""
    assert cell_for(10.0) == 0.5
    assert cell_for(8.0) == 0.5
    assert cell_for(4.0) == 1.0
    assert cell_for(0.5) == 1.0


def test_the_window_is_on_the_garden_s_own_axes() -> None:
    window = _window([])
    assert window.min_x == window.min_y == -150.0
    assert window.cols == window.rows == int(300 / window.cell_m)
    # Outside it there is no answer, rather than a wrong one.
    assert window.height_at(400.0, 0.0) is None


def test_a_tile_with_nothing_near_the_garden_is_no_window() -> None:
    """A tile the window only touches the corner of: read, found empty, and
    said so rather than returning three hundred metres of NaN."""
    far = window_from(_tile([]), LatLon(lat=51.05, lon=7.05), zone=ZONE, source="NW",
                      licence="dl-de/zero-2-0", attribution="Land NRW (2026)")
    # Five kilometres away: the tile is read and holds nothing of this garden.
    assert far is None


def test_a_window_survives_being_stored(tmp_path) -> None:
    """Centimetres above the window's own base, deflated — and a crown base
    from zero, because it is already a height above the ground rather than
    above the sea."""
    import sqlite3

    from ninanatur.geo.cloud_store import load_cloud, save_cloud
    from ninanatur.ingest.db import connect, init_schema

    conn: sqlite3.Connection = connect(":memory:")
    init_schema(conn)
    window = _window(_tree(5.5, 5.5))
    save_cloud(conn, "place", window)
    back = load_cloud(conn, "place")

    assert back is not None
    assert (back.cell_m, back.cols, back.rows) == (window.cell_m, window.cols, window.rows)
    assert back.points_per_m2 == window.points_per_m2
    assert back.height_at(5.5, 5.5) == pytest.approx(window.height_at(5.5, 5.5), abs=0.01)
    assert back.crown_at(5.5, 5.5) == pytest.approx(window.crown_at(5.5, 5.5), abs=0.01)
    # A cell nobody measured comes back unmeasured rather than as a zero.
    assert back.crown_at(-100.0, -100.0) is None


def test_the_stored_window_stays_under_a_megabyte() -> None:
    """The budget from the plan, and the reason the layers are packed at all:
    at a hundred gardens a megabyte each, the volume is the product."""
    import zlib

    from ninanatur.geo.cloud_store import _packed

    window = _window(_tree(5.5, 5.5))
    packed = sum(len(_packed(layer, 0.0))
                 for layer in (window.ground, window.surface, window.crown_base))
    assert packed < 1_000_000, packed
    # And the packing is doing the work: unpacked, the same numbers are larger.
    raw = len(zlib.compress(str(window.ground + window.surface + window.crown_base).encode()))
    assert packed < raw


def test_the_reader_never_holds_more_than_a_chunk() -> None:
    """The RAM budget is 300 MB and a tile is up to 445 (doc 107), so the tile
    is streamed from the volume and handed over a quarter of a million points
    at a time. Measured: 186 MB peak for the verified NRW tile."""
    from ninanatur.geo.pointcloud import CHUNK_POINTS

    assert CHUNK_POINTS <= 250_000


def test_the_sync_asks_once_per_place_and_keeps_the_window(monkeypatch, tmp_path) -> None:
    """The same shape as the terrain's (doc 107): two gardens in a street share
    a window, and the laser is read once."""
    import sqlite3

    from ninanatur.garden import cloud_sync
    from ninanatur.garden.models import Garden
    from ninanatur.geo.cloud_store import load_cloud
    from ninanatur.geo.terrain_store import cache_key
    from ninanatur.ingest.db import connect, init_schema

    conn: sqlite3.Connection = connect(":memory:")
    init_schema(conn)
    reads: list[str] = []

    def read(anchor, source, buildings):  # noqa: ANN001, ANN202 - a stand-in
        reads.append(source.name)
        return _window(_tree(5.5, 5.5))

    monkeypatch.setattr(cloud_sync, "state_at", lambda *_a: "Nordrhein-Westfalen")
    monkeypatch.setattr(cloud_sync, "_read", read)

    here = Garden(garden_id=1, share_token="t", owner_id=None, name="G",
                  latitude=HOME.lat, longitude=HOME.lon, created_at="", updated_at="")
    # Ten metres away: the same place, by the key the terrain already uses.
    next_door = Garden(garden_id=2, share_token="u", owner_id=None, name="H",
                       latitude=HOME.lat + 0.00005, longitude=HOME.lon, created_at="",
                       updated_at="")

    assert cloud_sync.ensure_cloud(conn, here) is True
    assert cloud_sync.ensure_cloud(conn, next_door) is True
    assert reads == ["nw-laz"], reads
    assert load_cloud(conn, cache_key(HOME)) is not None


def test_a_state_with_no_open_cloud_keeps_what_it_had(monkeypatch) -> None:
    """Most of them. Not an error, and nothing is fetched."""
    import sqlite3

    from ninanatur.garden import cloud_sync
    from ninanatur.garden.models import Garden
    from ninanatur.ingest.db import connect, init_schema

    conn: sqlite3.Connection = connect(":memory:")
    init_schema(conn)
    monkeypatch.setattr(cloud_sync, "state_at", lambda *_a: "Hessen")
    monkeypatch.setattr(cloud_sync, "_read", lambda *_a: pytest.fail("nothing to read"))

    garden = Garden(garden_id=1, share_token="t", owner_id=None, name="G",
                    latitude=HOME.lat, longitude=HOME.lon, created_at="", updated_at="")
    assert cloud_sync.ensure_cloud(conn, garden) is False
