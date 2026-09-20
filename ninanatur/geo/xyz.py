"""A height grid published as one line per cell — Wave 25, feature 1.

The last format standing between this project and the whole country. Where most
states publish a GeoTIFF, several publish plain text: `easting northing height`,
a million lines to the square kilometre, twenty-eight megabytes of ASCII for
four of binary. Bremen and Schleswig-Holstein publish *only* that, which is why
they were the last two states with no ground.

Three things were measured rather than assumed, on **2026-09-20**:

- **How to parse it.** `np.fromstring(..., sep=" ")` reads a square kilometre in
  **0.21 s**; `np.loadtxt` takes 2.86 s and splitting the bytes into tokens
  costs 160 MB of peak against 48. It also tolerates every separator these
  states use — one space, several, a tab, CRLF — and raises on anything else
  rather than quietly reading it wrong.
- **What precision it needs.** A northing of 5,475,999.5 survives float32 here
  and stops doing so at about 8.4 million, which is outside Germany but not
  outside a typo. Coordinates are read as float64 and only the heights kept as
  float32, which costs nothing in time and 24 MB at the peak.
- **That the file may not end where the grid does.** Schleswig-Holstein glues
  an HTML footer onto every download. Cutting at it is not enough — the cut has
  to fall back to the last complete line, or the last number is half a number.

**Placed by coordinate, not by counting.** A state that omits its unsurveyed
cells — which a coastal or border tile may well do — would otherwise shift every
row after the gap. Reading each line's own easting and northing costs one pass
and makes a gap a gap.
"""
from __future__ import annotations

import numpy as np

from ninanatur.geo.tiff import MAX_PIXELS, NO_DATA, Raster, TiffError

#: A height never contains one of these, so the first is where the grid stops
#: and something else begins.
NOT_A_NUMBER = b"<"


def _grid_part(data: bytes) -> bytes:
    """The text up to the last complete line before anything non-numeric."""
    stop = data.find(NOT_A_NUMBER)
    if stop < 0:
        return data
    return data[: data.rfind(b"\n", 0, stop) + 1]


def read_grid(data: bytes, *, cell_m: float, max_pixels: int = MAX_PIXELS) -> Raster:
    """Decode a text height grid into a north-up raster of metres.

    The same shape `read_raster` returns, so everything downstream — the paste,
    the resample, the window — cannot tell which kind of file it came from.
    """
    body = _grid_part(data)
    if not body.strip():
        raise TiffError("no grid in this document")
    try:
        flat = np.fromstring(body, dtype=np.float64, sep=" ")  # noqa: NPY003 - text mode
    except ValueError as broken:
        raise TiffError(f"not a grid this can read: {broken}") from broken
    if flat.size == 0 or flat.size % 3:
        raise TiffError(f"{flat.size} numbers is not whole rows of easting, northing, height")

    trio = flat.reshape(-1, 3)
    east, north, height = trio[:, 0], trio[:, 1], trio[:, 2]
    west, top = east.min(), north.max()
    width = int(round((east.max() - west) / cell_m)) + 1
    rows = int(round((top - north.min()) / cell_m)) + 1
    if width < 1 or rows < 1 or width * rows > max_pixels:
        raise TiffError(f"a grid of {width}x{rows} cells is not a window")

    # Row 0 is the north edge, as every raster here is, and each value goes
    # where its own coordinates put it — so a state that omits its unsurveyed
    # cells leaves holes rather than shifting everything after them.
    values = np.full((rows, width), np.nan, dtype="float32")
    col = np.rint((east - west) / cell_m).astype(np.intp)
    row = np.rint((top - north) / cell_m).astype(np.intp)
    values[row, col] = height.astype("float32")
    values[values == NO_DATA] = np.nan
    return Raster(width=width, height=rows, values=values)


__all__ = ["NOT_A_NUMBER", "read_grid"]
