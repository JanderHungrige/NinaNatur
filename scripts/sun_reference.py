"""Write `tests/fixtures/sun_reference.json`: the sun's place, from pvlib.

    uv run --no-project --with pvlib python -m scripts.sun_reference

The light model computes the sun with NOAA's algorithm (`solar/position.py`),
and until Wave 26 it was checked only against physics: the sun is due south at
its highest, overhead at the equator at the equinox. Those catch a sign error,
not a convention error that stays plausible. This table is an independent
implementation's answer — NREL's Solar Position Algorithm, as pvlib (BSD)
computes it — for 200 moments and places in Germany, and
`tests/test_sun_reference.py` holds the model to it (doc 115).

A table rather than pvlib in CI: pvlib brings SciPy and h5py into the dev lock
for one test, and a table cannot change under the test when pvlib moves. SPA
is deterministic, so what it says for a moment is what it will always say.

The elevation is the true one, without refraction, because the model has none
(`position.py`); the azimuth is clockwise from north in both.
"""
from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sun_reference.json"
COUNT = 200
SEED = 26
#: Germany's box, and a window of years the NOAA algorithm is stated for.
SOUTH, NORTH, WEST, EAST = 47.27, 55.06, 5.87, 15.04
FIRST, LAST = datetime(2020, 1, 1, tzinfo=UTC), datetime(2036, 1, 1, tzinfo=UTC)
#: Below this the sun counts for nothing in the model, and near the horizon the
#: two algorithms are asked a question nobody reads the answer to.
LOWEST = 1.0


def _candidates(rng: random.Random) -> list[tuple[float, float, datetime]]:
    """To the second: the drawing's moment (`solar/drawing.py`) has seconds in
    it, and a table of whole minutes never asks the model about them (review,
    2026-09-22)."""
    span = int((LAST - FIRST).total_seconds())
    return [
        (round(rng.uniform(SOUTH, NORTH), 4), round(rng.uniform(WEST, EAST), 4),
         FIRST + timedelta(seconds=rng.randrange(span)))
        for _ in range(COUNT * 4)
    ]


def main() -> int:
    import pandas as pd
    import pvlib

    rows: list[list[Any]] = []
    for lat, lon, when in _candidates(random.Random(SEED)):
        at = pd.DatetimeIndex([when])
        sun = pvlib.solarposition.get_solarposition(at, lat, lon, method="nrel_numpy")
        elevation = float(sun["elevation"].iloc[0])
        if elevation < LOWEST:
            continue
        rows.append([lat, lon, when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                     round(elevation, 4), round(float(sun["azimuth"].iloc[0]), 4)])
        if len(rows) == COUNT:
            break
    head = {
        "source": f"pvlib {pvlib.__version__}, solarposition.get_solarposition("
                  "method='nrel_numpy'): NREL SPA, true elevation (no refraction), "
                  "azimuth clockwise from north",
        "made_by": "python -m scripts.sun_reference",
        "columns": ["latitude", "longitude", "utc", "elevation", "azimuth"],
    }
    # One moment per line, so a regenerated table reads as a diff of moments.
    lines = [f" {json.dumps(k)}: {json.dumps(v)}," for k, v in head.items()]
    body = ",\n".join(f"  {json.dumps(row)}" for row in rows)
    OUT.write_text("{\n" + "\n".join(lines) + '\n "rows": [\n' + body + "\n ]\n}\n")
    print(f"{len(rows)} moments -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
