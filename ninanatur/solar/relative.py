"""What reaches a cell, as a share of open ground — Wave 26, feature 3 (doc 118).

Ellenberg defined his light value on relative illuminance: the light at a
plant's place as a share of the light in the open. Light is the sun and the
sky, and the climate decides the mix: in Kiel the sky weighs more than in
Freiburg. Month by month,

    light(cell) = D · direct share(cell) + Hd · sky share(cell)

with the climate's direct and diffuse light on level ground, D = H·(1 − Kd) and
Hd = H·Kd (`solar.climate`), the direct share what the clear-sky beam brings
to the cell's own surface over what it brings to open level ground (doc 119:
a low sun brings less than a high one, a slope turned away takes less of it),
and the sky share its sky-view factor (`solar.sky`). Open ground has
both shares 1, so its light is H, and relative illuminance is the months'
light summed over theirs.

Beside it, the hours a gardener would count on: the cell's geometric sun hours
times the share of possible sunshine the climate actually delivers — "7.5 h
in June rather than 15".

This does not yet decide the light value a species is matched by (doc 118).
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass

import numpy as np

from ninanatur.solar.beam import beam
from ninanatur.solar.climate import Climate
from ninanatur.solar.raster import (
    LEVEL,
    Directions,
    Incidence,
    Moments,
    Part,
    Plane,
    point_sums,
    point_sweep,
)
from ninanatur.solar.raster_grid import Cells, grid_sums, grid_sweep
from ninanatur.solar.sky import REINHART, TREGENZA, sky_directions

#: A month with crowns in leaf, and one without (`canopies`).
LEAF_MONTH = 7
BARE_MONTH = 3


@dataclass(frozen=True)
class SkyLight:
    """Per cell (or for one point): the sun, the sky, and their mix."""

    morning: np.ndarray
    afternoon: np.ndarray
    #: The sky-view factor, 0–1: for one month with the crowns as they are
    #: then, for the season with the crowns in leaf.
    sky: np.ndarray
    #: Relative illuminance over the months sampled: 1 on open level
    #: ground, and above it on a surface turned towards the sun (doc 119).
    relative: np.ndarray
    #: Mean daily hours of sunshine to expect, cloud included.
    expected: np.ndarray


def _months(moments: Moments) -> list[int]:
    return [m for m in range(1, 13) if len(moments.month_days) > m and moments.month_days[m]]


def _by_month(moments: Moments, months: list[int]) -> Directions:
    """The sun's moments, each a sample's share of an hour, summed by month
    and by half of the day: group 2i the morning of months[i], 2i + 1 its
    afternoon."""
    index = {m: i for i, m in enumerate(months)}
    group = np.array([index[int(m)] * 2 + (0 if early else 1)
                      for m, early in zip(moments.month, moments.morning, strict=True)], dtype=int)
    return Directions(azimuth=moments.azimuth, altitude=moments.altitude, month=moments.month,
                      weight=np.full(moments.azimuth.shape, moments.minute_step / 60),
                      group=group.reshape(-1), groups=2 * len(months))


def _incidence(moments: Moments, months: list[int]) -> Incidence:
    """Each moment's clear-sky beam, summed by month (doc 119)."""
    index = {m: i for i, m in enumerate(months)}
    return Incidence(beam=beam(moments.altitude),
                     group=np.array([index[int(m)] for m in moments.month], dtype=int),
                     groups=len(months))


def _open_energy(moments: Moments, months: list[int]) -> np.ndarray:
    """(months,): what the beam brings to open level ground in each month, the
    reference a cell's energy is a share of."""
    level = beam(moments.altitude) * np.sin(np.radians(moments.altitude))
    return np.array([float(level[moments.month == m].sum()) for m in months])


def _in_leaf(month: int) -> bool:
    """Whether crowns wear their leaves in this month (`shading.passes`)."""
    from ninanatur.solar.shading import passes

    return passes(1.0, 0.0, month) == 1.0


def _skies(months: list[int], seasonal: bool) -> tuple[dict[bool, Directions], bool]:
    """Which skies to sweep — in leaf, bare — and which of them a map reports:
    a month's own, and the season's in leaf. The one reported is Reinhart's
    finer sky, since a light value may be read from it; the season's other,
    which only mixes into three months' light, is Tregenza's. Without a
    deciduous crown the two are the same sky, swept once."""
    shown = _in_leaf(months[0]) if len(months) == 1 else True
    wanted = {_in_leaf(m) for m in months} | {shown} if seasonal else {shown}
    return {leafy: sky_directions(LEAF_MONTH if leafy else BARE_MONTH,
                                  split=REINHART if leafy == shown else TREGENZA)
            for leafy in wanted}, shown


def _mix(sums: np.ndarray, energy: np.ndarray, skies: dict[bool, np.ndarray], shown: bool,
         moments: Moments, months: list[int], climate: Climate) -> SkyLight:
    """From the sun's hours by month and half, its energy by month, and the
    skies, the rest. The sun's share of a month is its energy's (doc 119)."""
    first = skies[shown]
    light = np.zeros(first.shape)
    open_light = 0.0
    expected = np.zeros(first.shape)
    calendar_days = 0
    reference = _open_energy(moments, months)
    for i, month in enumerate(months):
        days = moments.month_days[month]
        hours = (sums[2 * i] + sums[2 * i + 1]) / days
        possible = float(np.sum(moments.month == month)) * moments.minute_step / 60 / days
        direct_share = energy[i] / reference[i] if reference[i] else np.zeros(hours.shape)
        sky = skies.get(_in_leaf(month), first)
        k = climate.months.index(month)
        radiation, diffuse = climate.global_kwh_m2[k], climate.diffuse_fraction[k]
        light += radiation * ((1 - diffuse) * direct_share + diffuse * sky)
        open_light += radiation
        in_month = calendar.monthrange(2026, month)[1]
        sunny = climate.sunshine_h[k] / (possible * in_month) if possible else 0.0
        expected += hours * min(sunny, 1.0) * in_month
        calendar_days += in_month
    return SkyLight(
        morning=sums[0::2].sum(axis=0) / moments.days,
        afternoon=sums[1::2].sum(axis=0) / moments.days,
        sky=first, relative=light / open_light if open_light else light,
        expected=expected / calendar_days if calendar_days else expected,
    )


def grid_sky_light(parts: list[Part], moments: Moments, cells: Cells,
                   climate: Climate) -> SkyLight:
    """Every cell's sun, sky and mix, over the moments' months."""
    months = _months(moments)
    sums, energy = grid_sweep(parts, _by_month(moments, months), cells,
                              _incidence(moments, months))
    wanted, shown = _skies(months, _seasonal(parts))
    skies = {leafy: grid_sums(parts, sky, cells)[0] for leafy, sky in wanted.items()}
    return _mix(sums, energy, skies, shown, moments, months, climate)


def point_sky_light(parts: list[Part], moments: Moments, climate: Climate, x: float,
                    y: float, z: float = 0.0, ring: list[float] | None = None,
                    owner: int | None = None, plane: Plane = LEVEL) -> SkyLight:
    """The same for one point — a raised bed, a bed narrower than a cell —
    standing on a surface of its own (`raster.plane_of`)."""
    months = _months(moments)
    sums, energy = point_sweep(parts, _by_month(moments, months), x, y, z, ring, owner,
                               _incidence(moments, months), plane)
    wanted, shown = _skies(months, _seasonal(parts))
    skies = {leafy: point_sums(parts, sky, x, y, z, ring, owner)
             for leafy, sky in wanted.items()}
    return _mix(sums[:, None], energy[:, None], skies, shown, moments, months, climate)


def _seasonal(parts: list[Part]) -> bool:
    """Whether any crown drops its leaves, so that the sky changes with them."""
    return any(part.bare_transmission is not None for part in parts)


__all__ = ["SkyLight", "grid_sky_light", "point_sky_light"]
