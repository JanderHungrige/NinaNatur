"""The tile cache on the volume — Wave 25, feature 1 (doc 103).

A tile is megabytes and never changes once written. The cache therefore has
three jobs and this file is about all three: fetch once, stay under its cap,
and never leave half a file behind that looks like a whole one.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from geokachel.tile_cache import TileCache


def counting(payloads: dict[str, bytes], seen: list[str]):
    def fetch(url: str) -> bytes:
        seen.append(url)
        return payloads[url]
    return fetch


def test_a_tile_is_fetched_once_and_then_read(tmp_path: Path) -> None:
    """Two gardens in the same kilometre ask nobody anything the second time."""
    seen: list[str] = []
    cache = TileCache(tmp_path, cap_bytes=1_000_000)
    fetch = counting({"https://x/690_5334.tif": b"ground"}, seen)
    first = cache.get("by/dgm1/690_5334.tif", "https://x/690_5334.tif", fetch)
    second = cache.get("by/dgm1/690_5334.tif", "https://x/690_5334.tif", fetch)
    assert first == second == b"ground"
    assert seen == ["https://x/690_5334.tif"]


def test_the_cap_drops_the_oldest_first(tmp_path: Path) -> None:
    """Not the least recently used: that needs a write on every read, and a
    cache that writes when it is read is a cache that wears the volume."""
    # Three tiles of a hundred bytes and room for two.
    cache = TileCache(tmp_path, cap_bytes=250)
    for index, name in enumerate(("a", "b", "c")):
        cache.get(f"by/dgm1/{name}.tif", f"https://x/{name}", lambda _u, n=name: n.encode() * 100)
        # Distinct modification times, oldest first, without sleeping.
        os.utime(tmp_path / "by" / "dgm1" / f"{name}.tif", (1_000 + index, 1_000 + index))
        cache.tidy()
    kept = sorted(p.name for p in (tmp_path / "by" / "dgm1").glob("*.tif"))
    assert kept == ["b.tif", "c.tif"], kept
    assert cache.bytes_held() <= 250


def test_a_tile_is_written_whole_or_not_at_all(tmp_path: Path) -> None:
    """Half a tile that looks like a tile is the failure that costs a day."""
    cache = TileCache(tmp_path, cap_bytes=1_000)

    def breaks(_url: str) -> bytes:
        raise TimeoutError("the state's portal went away")

    with pytest.raises(TimeoutError):
        cache.get("by/dgm1/690_5334.tif", "https://x/690", breaks)
    assert list(tmp_path.rglob("*.tif")) == []
    assert list(tmp_path.rglob("*.part")) == []


def test_a_key_cannot_climb_out_of_the_cache(tmp_path: Path) -> None:
    """The key is built from a registry template and two integers, and this is
    what makes that a guarantee rather than a habit."""
    cache = TileCache(tmp_path, cap_bytes=1_000)
    for key in ("../escape.tif", "by/../../escape.tif", "/etc/passwd"):
        with pytest.raises(ValueError, match="key"):
            cache.get(key, "https://x/1", lambda _u: b"no")


def test_an_empty_answer_is_not_cached(tmp_path: Path) -> None:
    """A zero-byte tile is a portal having a bad day, not this kilometre's
    ground being empty — and cached, it would be wrong until the cap evicts it."""
    cache = TileCache(tmp_path, cap_bytes=1_000)
    with pytest.raises(ValueError, match="empty"):
        cache.get("by/dgm1/690_5334.tif", "https://x/690", lambda _u: b"")
    assert list(tmp_path.rglob("*.tif")) == []
