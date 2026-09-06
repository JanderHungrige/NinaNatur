"""Fetching object heights, and the subtraction that is easy to do twice."""
from __future__ import annotations

import struct

import numpy as np
import pytest

from ninanatur.geo.projection import LatLon
from ninanatur.geo.surface import fetch_surface
from ninanatur.geo.surface_sources import by_state
from ninanatur.geo.terrain import TerrainWindow

WEST = LatLon(lat=51.0, lon=6.0)
NRW = by_state("Nordrhein-Westfalen")      # nDOM, already normalised
NI = by_state("Niedersachsen")             # DOM, needs the terrain subtracted
assert NRW is not None and NI is not None


def _tiff(values: np.ndarray) -> bytes:
    height, width = values.shape
    body = values.astype("<f4").tobytes()
    entries = [(256, width), (257, height), (258, 32), (259, 1),
               (273, 8), (277, 1), (278, height), (279, len(body)), (339, 3)]
    out = bytearray(b"II\x2a\x00") + struct.pack("<I", 8 + len(body)) + body
    out += struct.pack("<H", len(entries))
    for tag, value in entries:
        kind = 4 if tag in (273, 279) else 3
        raw = struct.pack("<I" if kind == 4 else "<H", value)
        out += struct.pack("<HHI", tag, kind, 1) + raw + b"\x00" * (4 - len(raw))
    return bytes(out + struct.pack("<I", 0))


def _flat(value: float, size: int, cell: float) -> bytes:
    return _tiff(np.full((size, size), value, dtype="<f4"))


def _ground(height: float, cell: float = 1.0, size: int = 240) -> TerrainWindow:
    return TerrainWindow(
        min_x=-size / 2 * cell, min_y=-size / 2 * cell, cell_m=cell,
        cols=size, rows=size, heights=[height] * (size * size),
        source="Test", licence="—", attribution="—", vertical_step_m=0.01,
    )


def test_a_normalised_source_is_taken_as_it_comes() -> None:
    """NRW's nDOM already is height above ground. Subtracting the terrain from
    it would give negative buildings — the failure that looks like a bug in the
    shading model rather than in the fetch."""
    window = fetch_surface(WEST, NRW, _ground(300.0), fetch=lambda url: _flat(8.0, 440, 0.5))

    assert window is not None
    assert window.at(0.0, 0.0) == pytest.approx(8.0)


def test_a_raw_surface_has_the_ground_taken_off_it() -> None:
    """Niedersachsen's DOM is metres above sea level. A 55 m surface over 47 m
    of terrain is an eight-metre house."""
    window = fetch_surface(WEST, NI, _ground(47.0), fetch=lambda url: _flat(55.0, 240, 1.0))

    assert window is not None
    assert window.at(0.0, 0.0) == pytest.approx(8.0, abs=0.01)


def test_a_raw_surface_without_terrain_is_refused() -> None:
    """A state of the world — a garden whose terrain fetch failed — rather than
    a programming error, so None rather than an exception."""
    assert fetch_surface(WEST, NI, None, fetch=lambda url: _flat(55.0, 240, 1.0)) is None


def test_a_normalised_source_needs_no_terrain_at_all() -> None:
    window = fetch_surface(WEST, NRW, None, fetch=lambda url: _flat(8.0, 440, 0.5))
    assert window is not None


def test_a_surface_below_its_own_terrain_reads_as_bare_ground() -> None:
    """The two models disagreeing at an edge, not a hole in the ground."""
    window = fetch_surface(WEST, NI, _ground(50.0), fetch=lambda url: _flat(49.6, 240, 1.0))

    assert window is not None
    assert window.at(0.0, 0.0) == pytest.approx(0.0)


def test_the_finer_source_keeps_its_own_cell_size() -> None:
    """NRW's nDOM is half a metre where its terrain is one. A caller that
    assumed the two rasters shared a grid would be wrong there first."""
    window = fetch_surface(WEST, NRW, None, fetch=lambda url: _flat(3.0, 440, 0.5))

    assert window is not None
    assert window.cell_m == 0.5
    assert window.cols == 400, "200 m of window at half a metre"


def test_a_point_outside_the_window_is_none() -> None:
    window = fetch_surface(WEST, NRW, None, fetch=lambda url: _flat(3.0, 440, 0.5))
    assert window is not None
    assert window.at(500.0, 0.0) is None


def test_the_window_carries_its_credit() -> None:
    window = fetch_surface(WEST, NRW, None, fetch=lambda url: _flat(3.0, 440, 0.5))
    assert window is not None
    assert window.attribution
    assert window.licence
