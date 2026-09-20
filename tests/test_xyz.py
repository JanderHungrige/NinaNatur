"""A height grid published as one line per cell — Wave 25, feature 1 (doc 103).

The grids are built here. What is checked is what these states actually do:
separators that vary, an HTML footer glued onto the download, unsurveyed cells
either omitted or marked, and a square kilometre that has to be read in well
under a second.
"""
from __future__ import annotations

import time

import numpy as np
import pytest
from geokachel.tiff import TiffError
from geokachel.xyz import read_grid


def _grid(west: int = 348_000, south: int = 5_475_000, side: int = 4,
          cell: float = 1.0, sep: str = " ", end: str = "\n") -> bytes:
    """A regular grid, cell centres on the half metre, north row first — the
    order these states write and the order the raster keeps."""
    lines = []
    for r in range(side):
        north = south + side - 0.5 - r
        for c in range(side):
            lines.append(sep.join((f"{west + c + 0.5:.2f}", f"{north:.2f}",
                                   f"{100 + r * 10 + c:.2f}")))
    return (end.join(lines) + end).encode()


def test_a_grid_becomes_a_north_up_raster() -> None:
    """Row 0 is the north edge, as it is for every raster here, so the paste
    and the resample cannot tell a text grid from a GeoTIFF."""
    raster = read_grid(_grid(), cell_m=1.0)
    assert (raster.width, raster.height) == (4, 4)
    assert raster.values[0][0] == pytest.approx(100.0)   # north-west
    assert raster.values[0][3] == pytest.approx(103.0)   # north-east
    assert raster.values[3][0] == pytest.approx(130.0)   # south-west
    assert np.isfinite(raster.values).all()


@pytest.mark.parametrize(("sep", "end"), [
    (" ", "\n"), ("\t", "\n"), ("   ", "\n"), (" ", "\r\n"),
])
def test_every_separator_these_states_use(sep: str, end: str) -> None:
    """One space, a tab, several spaces, CRLF. They disagree, and none of the
    disagreements is worth a per-state reader."""
    raster = read_grid(_grid(sep=sep, end=end), cell_m=1.0)
    assert raster.values[0][0] == pytest.approx(100.0)
    assert raster.values[3][3] == pytest.approx(133.0)


def test_a_separator_nobody_uses_is_refused_rather_than_misread() -> None:
    """A semicolon would be a different format. Reading it as whitespace would
    silently produce heights of nonsense, which is the failure to avoid."""
    with pytest.raises(TiffError):
        read_grid(_grid(sep=";"), cell_m=1.0)


def test_the_html_footer_a_download_arrives_with_is_cut_off() -> None:
    """Schleswig-Holstein appends one to every download. A naive cut at the
    tag leaves the last line half-written, so the cut falls back to the last
    complete line."""
    served = _grid() + b"<!DOCTYPE html><html>Zur\xc3\xbcck zum Downloadportal</html>"
    raster = read_grid(served, cell_m=1.0)
    assert (raster.width, raster.height) == (4, 4)
    assert raster.values[3][3] == pytest.approx(133.0)


def test_a_footer_that_interrupts_a_line_still_leaves_whole_rows() -> None:
    body = _grid()
    served = body[:-6] + b"<!DOCTYPE html>"      # cut mid-number
    raster = read_grid(served, cell_m=1.0)
    assert raster.width == 4
    assert np.isnan(raster.values[3][3]), "the interrupted cell is unknown, not wrong"


def test_an_apology_with_no_grid_in_it_is_refused() -> None:
    """A stale row answers 200 with HTML and no numbers at all."""
    with pytest.raises(TiffError, match="no grid"):
        read_grid(b"<!DOCTYPE html><html>Die Datei ist veraltet.</html>", cell_m=1.0)


def test_a_cell_the_state_left_out_is_a_hole_not_a_shift() -> None:
    """A coastal or border tile may simply omit what nobody surveyed. Counting
    lines would move every cell after the gap; reading each line's own
    coordinates leaves the gap where it is."""
    lines = _grid().decode().splitlines()
    del lines[5]                                   # row 1, column 1
    raster = read_grid(("\n".join(lines) + "\n").encode(), cell_m=1.0)
    assert (raster.width, raster.height) == (4, 4)
    assert np.isnan(raster.values[1][1])
    assert raster.values[1][2] == pytest.approx(112.0), "the rest did not shift"
    assert raster.values[3][3] == pytest.approx(133.0)


def test_the_no_data_marker_is_unknown_rather_than_ten_thousand_below_the_sea() -> None:
    body = _grid().replace(b"100.00", b"-9999.00")
    raster = read_grid(body, cell_m=1.0)
    assert np.isnan(raster.values[0][0])
    assert raster.values[0][1] == pytest.approx(101.0)


def test_a_grid_larger_than_a_window_is_refused_before_it_is_built() -> None:
    """The same guard the TIFF reader keeps: a header claiming more than any
    caller asks for is refused while it is still a header."""
    with pytest.raises(TiffError, match="is not a window"):
        read_grid(_grid(side=4), cell_m=1.0, max_pixels=4)


def test_numbers_that_are_not_whole_rows_are_refused() -> None:
    with pytest.raises(TiffError, match="whole rows"):
        read_grid(b"348000.50 5475000.50\n", cell_m=1.0)


def test_a_square_kilometre_is_read_in_well_under_a_second() -> None:
    """Twenty-eight megabytes of ASCII, a million lines. Measured at 0.21 s;
    `np.loadtxt` takes 2.86 s for the same file, which is why it is not used.
    The bound is loose enough never to flake and far tighter than the slow way.
    """
    body = _grid(side=1000, cell=1.0)
    assert body.count(b"\n") == 1_000_000

    started = time.monotonic()
    raster = read_grid(body, cell_m=1.0, max_pixels=2_000_000)
    took = time.monotonic() - started

    assert (raster.width, raster.height) == (1000, 1000)
    assert took < 2.0, f"a square kilometre took {took:.2f}s"


def test_the_half_metre_northings_of_a_real_tile_survive_the_parse() -> None:
    """A northing of 5,475,999.5 needs more than float32's seven digits to be
    sure of; coordinates are read as float64 so a cell lands where it belongs.
    """
    raster = read_grid(_grid(west=348_000, south=5_475_000, side=2), cell_m=1.0)
    assert (raster.width, raster.height) == (2, 2)
    assert raster.values[0][0] == pytest.approx(100.0)
    assert raster.values[1][1] == pytest.approx(111.0)


def test_the_header_line_bremen_writes_is_not_read_as_a_cell() -> None:
    """Bremen alone puts `x y z` above its first row."""
    raster = read_grid(b"x y z\n" + _grid(), cell_m=1.0)
    assert (raster.width, raster.height) == (4, 4)
    assert raster.values[0][0] == pytest.approx(100.0)


def test_an_easting_with_the_zone_glued_to_it_is_still_an_easting() -> None:
    """Bremerhaven writes `32466000.50` for 466 km east; every other state
    writes the metres alone. Read literally it is an easting thirty-two
    thousand kilometres out to sea, and the grid would be one cell wide."""
    zoned = _grid(west=466_000).replace(b"466", b"32466")
    raster = read_grid(zoned, cell_m=1.0)
    assert (raster.width, raster.height) == (4, 4)
    assert raster.values[0][0] == pytest.approx(100.0)
    assert raster.values[3][3] == pytest.approx(133.0)


def test_a_ragged_border_tile_is_read_at_its_true_size() -> None:
    """Measured on Schleswig-Holstein: border tiles carry 730,232 or 829,760
    lines rather than a million, with holes inside a row, and no NoData token
    — the cells are simply absent."""
    lines = _grid().decode().splitlines()
    kept = [ln for i, ln in enumerate(lines) if i not in (2, 3, 6, 9, 14)]
    raster = read_grid(("\r\n".join(kept) + "\r\n").encode(), cell_m=1.0)
    assert (raster.width, raster.height) == (4, 4)
    assert int(np.isnan(raster.values).sum()) == 5
    assert raster.values[0][1] == pytest.approx(101.0)
    assert raster.values[3][3] == pytest.approx(133.0)
