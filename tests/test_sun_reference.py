"""The sun's place, against an independent implementation (doc 115).

`test_solar_position.py` checks the NOAA algorithm against physics: due south
at the highest point, overhead at the equator at the equinox. That catches a
dropped equation of time or a flipped sign, but an error that stays plausible
passes all eleven of its tests: an equation of time at half its size, which
puts the sun 1.1° off here, or a moment's seconds ignored, 0.4° — and the
drawing's moment has seconds in it. This holds the model to NREL's Solar
Position Algorithm, as pvlib computed it for 200 moments to the second in
Germany's box (`scripts/sun_reference.py`, which says why it is a table).

Measured when the table was made: the two agree within 0.016°. The plan asked
for 0.5°; the bar is 0.05°, so a real regression cannot hide under it.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ninanatur.solar.position import Location, sun_position

TABLE = Path(__file__).parent / "fixtures" / "sun_reference.json"
TOLERANCE_DEG = 0.05


def _rows() -> list[list[Any]]:
    rows: list[list[Any]] = json.loads(TABLE.read_text())["rows"]
    return rows


def _around(a: float, b: float) -> float:
    """The angle between two azimuths, the short way round."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


def test_the_sun_is_where_nrel_puts_it() -> None:
    worst_altitude = worst_azimuth = 0.0
    for lat, lon, utc, elevation, azimuth in _rows():
        sun = sun_position(Location(lat, lon), datetime.fromisoformat(utc.replace("Z", "+00:00")))
        worst_altitude = max(worst_altitude, abs(sun.altitude - elevation))
        worst_azimuth = max(worst_azimuth, _around(sun.azimuth, azimuth))
    assert worst_altitude < TOLERANCE_DEG, f"altitude off by up to {worst_altitude:.3f}°"
    assert worst_azimuth < TOLERANCE_DEG, f"azimuth off by up to {worst_azimuth:.3f}°"


def test_the_table_covers_the_country_and_the_year() -> None:
    """A table of two hundred June noons in Berlin would check one case twice."""
    rows = _rows()
    assert len(rows) == 200
    lats = [r[0] for r in rows]
    lons = [r[1] for r in rows]
    months = {int(r[2][5:7]) for r in rows}
    assert max(lats) - min(lats) > 6 and max(lons) - min(lons) > 7
    assert months == set(range(1, 13))
    assert any(r[4] < 120 for r in rows) and any(r[4] > 240 for r in rows), "mornings and evenings"
    assert all(r[3] >= 1.0 for r in rows), "the sun is up in every row"


def test_the_table_is_what_its_script_writes() -> None:
    """Locations already rounded as `Location` rounds them, so the model is
    asked exactly the place the reference answered for."""
    for lat, lon, *_ in _rows():
        place = Location(lat, lon)
        assert (place.latitude, place.longitude) == (lat, lon)
