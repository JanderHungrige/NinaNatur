"""Write `ninanatur/data/climate_de.json.gz`: Germany's growing-season light climate.

    python -m scripts.dwd_climate

From the Deutscher Wetterdienst's Climate Data Center (CC BY 4.0; no robots.txt
on opendata.dwd.de), per 10 km cell of its 1 km Gauss–Krüger grid, for each
month from March to October (doc 118):

- global radiation on level ground, the 1991–2020 multi-annual mean, kWh/m²;
- the diffuse fraction: diffuse over global radiation, summed over 2015–2025
  (the DWD's diffuse grids begin in 2015);
- sunshine duration, the 1991–2020 multi-annual mean, hours.

Not PVGIS, which the plan named first: its host's robots.txt disallows every
agent (checked 2026-09-22), and this project fetches nothing a robots.txt
refuses. The DWD was the plan's second source; a climatology does not change
between two gardens, so it ships with the image instead of being fetched per
garden. Everything goes through `ingest/http.py`: a rerun costs no request.
"""
from __future__ import annotations

import gzip
import io
import json
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from ninanatur.ingest.http import get_bytes

BASE = "https://opendata.dwd.de/climate_environment/CDC/grids_germany"
OUT = Path(__file__).resolve().parent.parent / "ninanatur" / "data" / "climate_de.json.gz"
MONTHS = tuple(range(3, 11))
DIFFUSE_YEARS = tuple(range(2015, 2026))
#: 10 × 10 cells of 1 km: a climatology does not change across a village.
BLOCK = 10


def _grid(payload: bytes) -> tuple[dict[str, float], np.ndarray]:
    """An ESRI ASCII grid with the DWD's own header in front, from a zip or a
    gzip. Rows are turned to run from the south, as every grid here does."""
    if payload[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            text = archive.read(archive.namelist()[0]).decode("latin-1")
    else:
        text = gzip.decompress(payload).decode("latin-1")
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.upper().startswith("NCOLS"))
    header = {lines[i].split()[0].lower(): float(lines[i].split()[1])
              for i in range(start, start + 6)}
    values = np.array(" ".join(lines[start + 6:]).split(), dtype=float)
    grid = values.reshape(int(header["nrows"]), int(header["ncols"]))[::-1]
    return header, np.where(grid == header["nodata_value"], np.nan, grid)


def _blocks(grid: np.ndarray) -> np.ndarray:
    """The mean of each BLOCK × BLOCK square over the cells that have a value;
    NaN only where none has — the open sea, the far side of a border. An
    island's three cells are its climate: requiring half the square once gave
    Helgoland the country's mean (review, 2026-09-22)."""
    rows, cols = -(-grid.shape[0] // BLOCK) * BLOCK, -(-grid.shape[1] // BLOCK) * BLOCK
    padded = np.full((rows, cols), np.nan)
    padded[:grid.shape[0], :grid.shape[1]] = grid
    squares = padded.reshape(rows // BLOCK, BLOCK, cols // BLOCK, BLOCK).swapaxes(1, 2)
    squares = squares.reshape(rows // BLOCK, cols // BLOCK, BLOCK * BLOCK)
    counts = np.sum(~np.isnan(squares), axis=2)
    with np.errstate(invalid="ignore"):
        means = np.nanmean(np.where(counts[..., None] > 0, squares, 0.0), axis=2)
    means[counts == 0] = np.nan
    return means


def _fetch(path: str) -> tuple[dict[str, float], np.ndarray]:
    return _grid(get_bytes(f"{BASE}/{path}", max_bytes=20_000_000))


def _month(month: int) -> tuple[dict[str, float], dict[str, np.ndarray]]:
    header, radiation = _fetch(
        f"multi_annual/radiation_global/"
        f"grids_germany_multi_monthly_radiation_global_1991_2020_{month:02d}.zip")
    _, sunshine = _fetch(f"multi_annual/sunshine_duration/"
                         f"grids_germany_multi_annual_sunshine_duration_1991-2020_{month:02d}.asc.gz")
    diffuse_sum = np.zeros_like(radiation)
    global_sum = np.zeros_like(radiation)
    for year in DIFFUSE_YEARS:
        diffuse_sum += _fetch(f"monthly/radiation_diffuse/"
                              f"grids_germany_monthly_radiation_diffuse_{year}{month:02d}.zip")[1]
        global_sum += _fetch(f"monthly/radiation_global/"
                             f"grids_germany_monthly_radiation_global_{year}{month:02d}.zip")[1]
    return header, {"global_kwh_m2": _blocks(radiation), "sunshine_h": _blocks(sunshine),
                    "diffuse_fraction": _blocks(diffuse_sum) / _blocks(global_sum)}


def _listed(grid: np.ndarray, digits: int) -> list[float | None]:
    return [None if np.isnan(v) else round(float(v), digits) for v in grid.ravel()]


def main() -> int:
    months: dict[int, dict[str, np.ndarray]] = {}
    header: dict[str, float] = {}
    for month in MONTHS:
        header, months[month] = _month(month)
    shape = months[MONTHS[0]]["global_kwh_m2"].shape
    digits = {"global_kwh_m2": 1, "sunshine_h": 1, "diffuse_fraction": 3}
    document: dict[str, Any] = {
        "source": "Deutscher Wetterdienst, Climate Data Center: grids_germany — multi-annual "
                  "radiation_global and sunshine_duration 1991–2020; monthly radiation_diffuse "
                  f"and radiation_global {DIFFUSE_YEARS[0]}–{DIFFUSE_YEARS[-1]}",
        # SPDX, as every other source here; the deed, which CC BY asks to be
        # linked; and the DWD's own wording for values it did not publish as
        # they stand (dwd.de, "Vorlagen für Quellenvermerke": averaged values).
        "licence": "CC-BY-4.0",
        "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "Datenbasis: Deutscher Wetterdienst, Einzelwerte gemittelt",
        "made_by": "python -m scripts.dwd_climate",
        "made_at": datetime.now(UTC).date().isoformat(),
        "crs": "Gauss-Krüger, 3rd strip (EPSG:31467)",
        "x0": header["xllcorner"], "y0": header["yllcorner"],
        "cell_m": header["cellsize"] * BLOCK, "cols": shape[1], "rows": shape[0],
        "months": list(MONTHS),
        **{key: {str(m): _listed(months[m][key], d) for m in MONTHS}
           for key, d in digits.items()},
    }
    OUT.write_bytes(gzip.compress(json.dumps(document, separators=(",", ":")).encode(),
                                  mtime=0))
    print(f"{shape[1]} x {shape[0]} cells of {header['cellsize'] * BLOCK:.0f} m -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
