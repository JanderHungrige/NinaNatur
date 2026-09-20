"""Tiles kept on the volume, under a cap — Wave 25, feature 1 (doc 103).

A tile is megabytes: 2.5 MB of GeoTIFF for a Bavarian square kilometre, more
for anything richer. It must not land in the container layer, where a rolled
image loses it and a full disk is the whole deployment (plan 01, ST-07), so it
lives under the data volume beside the database.

Three jobs, and no more than three:

- **Fetch once.** Two gardens in the same kilometre want the same tile.
- **Stay under the cap**, dropping the oldest file first. Not the least
  recently *used*: that needs a write on every read, and a cache that writes
  when it is read is a cache that wears the volume. These entries never change
  once written, so age is enough.
- **Write whole or not at all** — to `.part`, then rename. Half a tile that
  looks like a tile is the failure that costs a day to find.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

#: What a key may contain: the registry's own template, and nothing that could
#: climb out of the cache root.
SAFE_KEY = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/"

Fetch = Callable[[str], bytes]


@dataclass(frozen=True)
class TileCache:
    """Tiles on disk, keyed by what they are rather than by who asked."""

    root: Path
    cap_bytes: int

    def get(self, key: str, url: str, fetch: Fetch) -> bytes:
        """This tile's bytes, from the volume or from its state's portal."""
        return self.fetched(key, lambda: fetch(url))

    def fetched(self, key: str, grab: Callable[[], bytes]) -> bytes:
        """The same, for a tile whose address is not a plain URL — a member
        read out of a remote archive over ranges, say (doc 103)."""
        path = self._path(key)
        if path.exists():
            return path.read_bytes()
        data = grab()
        if not data:
            # A portal having a bad day, not a kilometre with no ground in it.
            raise ValueError(f"empty answer for {key}")
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(f"{path.suffix}.part")
        part.write_bytes(data)
        part.replace(path)
        self.tidy()
        return data

    def path_for(self, key: str) -> Path:
        """Where this key lives on the volume, whether or not it is there yet.

        For a tile that arrives wrapped: the archive is fetched under its own
        key and the member is written out under this one (doc 103).
        """
        return self._path(key)

    def file_into(self, key: str, grab: Callable[[], bytes]) -> Path:
        """The same as `file_for`, for an address that is not a plain URL."""
        path = self._path(key)
        if not path.exists():
            self.fetched(key, grab)
        return path

    def file_for(self, key: str, url: str, fetch: Fetch) -> Path:
        """The same tile, as a file on the volume rather than as bytes.

        A laser tile is up to 445 MB (doc 107). Handing it over as bytes means
        holding all of it and then decoding it, which is the budget twice over;
        a reader that streams wants a path.
        """
        path = self._path(key)
        if not path.exists():
            self.get(key, url, fetch)
        return path

    def tidy(self) -> None:
        """Drop the oldest tiles until the cache is inside its cap."""
        files = sorted(
            (p for p in self.root.rglob("*") if p.is_file() and p.suffix != ".part"),
            key=lambda p: p.stat().st_mtime,
        )
        held = sum(p.stat().st_size for p in files)
        for oldest in files:
            if held <= self.cap_bytes:
                return
            held -= oldest.stat().st_size
            oldest.unlink(missing_ok=True)

    def bytes_held(self) -> int:
        return sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())

    def _path(self, key: str) -> Path:
        """Where this key lives, or an error. The key comes from a registry
        template and two integers; this is what makes that a guarantee."""
        if (key.startswith("/") or ".." in key.split("/")
                or any(character not in SAFE_KEY for character in key)):
            raise ValueError(f"unusable cache key: {key!r}")
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"unusable cache key: {key!r}")
        return path


def cache_at(data_dir: str | os.PathLike[str], cap_bytes: int) -> TileCache:
    """The deployment's tile cache: a folder beside the database, never a path
    from a request."""
    return TileCache(Path(data_dir) / "tiles", cap_bytes)


__all__ = ["TileCache", "cache_at"]
