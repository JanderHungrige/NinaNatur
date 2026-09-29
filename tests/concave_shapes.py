"""Random outlines of the kind OpenStreetMap draws, for the geometry tests.

L, U and T shapes at any angle, and star-shaped polygons (corners at sorted
random angles and random distances: always simple, nearly always concave).
Shared by the ray instrument (`test_concave_ray.py`, doc 115) and the drawn
shadow (`test_drawn_shadow.py`, doc 116). Not a test module: pytest collects
only `test_*`.
"""
from __future__ import annotations

import math
import random

Outline = list[tuple[float, float]]


def placed(shape: Outline, rng: random.Random) -> Outline:
    """Turned to a random angle and moved to a random spot."""
    turn = rng.uniform(0, 2 * math.pi)
    cx, cy = rng.uniform(-12, 12), rng.uniform(-12, 12)
    c, s = math.cos(turn), math.sin(turn)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in shape]


def orthogonal(rng: random.Random) -> Outline:
    """An L, a U or a T, arms of random length and thickness."""
    w, d = rng.uniform(6, 14), rng.uniform(6, 14)
    a, b = rng.uniform(2, w / 2), rng.uniform(2, d / 2)
    kind = rng.choice("LUT")
    if kind == "L":
        shape = [(0, 0), (w, 0), (w, b), (a, b), (a, d), (0, d)]
    elif kind == "U":
        shape = [(0, 0), (w, 0), (w, d), (w - a, d), (w - a, b), (a, b), (a, d), (0, d)]
    else:
        shape = [(0, d - b), (w / 2 - a / 2, d - b), (w / 2 - a / 2, 0), (w / 2 + a / 2, 0),
                 (w / 2 + a / 2, d - b), (w, d - b), (w, d), (0, d)]
    return [(x - w / 2, y - d / 2) for x, y in shape]


def star(rng: random.Random) -> Outline:
    n = rng.randint(5, 9)
    angles = sorted(rng.uniform(0, 2 * math.pi) for _ in range(n))
    return [(r * math.cos(t), r * math.sin(t))
            for t, r in ((t, rng.uniform(2.5, 9)) for t in angles)]


def scene(rng: random.Random) -> list[Outline]:
    """One to three outlines, each an orthogonal shape or a star."""
    return [placed(rng.choice([orthogonal, star])(rng), rng)
            for _ in range(rng.randint(1, 3))]
