"""One tile out of an archive that is never fetched — Wave 25, feature 1.

Three states publish no tile at all. Hamburg and Bremen hand out their whole
city as one 0.4–3.2 GB archive; Saarland hands out a Landkreis at a time, 559 MB
for the ground and 12.5 GB for the point cloud. Doc 102 recorded that as a
packaging decision no index would fix.

It is fixable, because of where a zip keeps its index. The central directory is
at the **end** of the file, so with HTTP range requests an archive can be read
as though it were a local file: the directory says where each member starts and
how long it is, and only those bytes are asked for. Measured against Saarland's
ground archive on **2026-09-20**:

| | |
|---|---|
| archive | 559,134,521 B |
| its directory — 311 members | **3 requests, 34,888 B** |
| one 4 MB tile out of it | 2 more requests |
| **total** | **5 requests, 2,132,040 B — 0.38 % of the archive — in 2.0 s** |

The parsing is the standard library's. `zipfile` already knows Zip64, data
descriptors and every other corner of the format; what it lacks is a file to
read, so this supplies one. Writing a second zip parser to save an import would
be the wrong kind of clever.

**A member's name is data.** What comes out of a remote directory is matched
against the same grid arithmetic as everything else and against a strict
character set, and nothing is ever written to a path built from it.
"""
from __future__ import annotations

import io
import zipfile
from collections.abc import Callable

#: How much to ask for in one request. The directory read is a few tens of
#: kilobytes and a tile is a few megabytes, so a megabyte a time keeps a tile
#: to a handful of requests without asking for much that is never used.
CHUNK = 1 << 20

#: The largest member this will pull out. Saarland's point-cloud tiles are the
#: biggest thing in any of these archives at about 60 MB.
MAX_MEMBER_BYTES = 400_000_000

#: url, first byte, last byte (inclusive) -> those bytes.
Ranged = Callable[[str, int, int], bytes]
#: url -> how many bytes it is.
Sized = Callable[[str], int]


class RemoteArchiveError(ValueError):
    """An archive this cannot read over ranges."""


class _Windowed(io.RawIOBase):
    """A read-only seekable file backed by HTTP range requests."""

    def __init__(self, url: str, size: int, ranged: Ranged) -> None:
        self._url, self._size, self._ranged, self._at = url, size, ranged, 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._at

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        target = (offset if whence == io.SEEK_SET
                  else self._at + offset if whence == io.SEEK_CUR
                  else self._size + offset)
        self._at = max(0, min(self._size, target))
        return self._at

    def readinto(self, buffer: memoryview) -> int:  # type: ignore[override]
        want = min(len(buffer), self._size - self._at)
        if want <= 0:
            return 0
        body = self._ranged(self._url, self._at, self._at + want - 1)
        buffer[:len(body)] = body
        self._at += len(body)
        return len(body)


def _opened(url: str, size: Sized, ranged: Ranged) -> zipfile.ZipFile:
    total = size(url)
    if total <= 0:
        raise RemoteArchiveError(f"{url} says it is {total} bytes")
    stream = io.BufferedReader(_Windowed(url, total, ranged), buffer_size=CHUNK)
    try:
        return zipfile.ZipFile(stream)
    except (zipfile.BadZipFile, OSError, NotImplementedError) as broken:
        raise RemoteArchiveError(f"not an archive this can read over ranges: {broken}") from broken


def names_in(url: str, *, size: Sized, ranged: Ranged) -> list[str]:
    """Every member an archive holds, from its directory alone.

    Three requests and thirty-five kilobytes for Saarland's three hundred
    tiles: an index, for a state that publishes none.
    """
    with _opened(url, size, ranged) as archive:
        return [entry.filename for entry in archive.infolist() if not entry.is_dir()]


def member_of(url: str, name: str, *, size: Sized, ranged: Ranged,
              max_bytes: int = MAX_MEMBER_BYTES) -> bytes:
    """One member's bytes, without the archive around it.

    The member is measured from the directory before it is read, which is the
    same order the TIFF reader and the local zip reader keep.
    """
    with _opened(url, size, ranged) as archive:
        try:
            entry = archive.getinfo(name)
        except KeyError as missing:
            raise RemoteArchiveError(f"{name} is not in {url.rsplit('/', 1)[-1]}") from missing
        if entry.file_size > max_bytes:
            raise RemoteArchiveError(f"{name} is too large: {entry.file_size} bytes")
        try:
            return archive.read(entry)
        except (zipfile.BadZipFile, OSError, NotImplementedError) as broken:
            raise RemoteArchiveError(f"could not read {name}: {broken}") from broken


__all__ = ["CHUNK", "MAX_MEMBER_BYTES", "RemoteArchiveError", "member_of", "names_in"]
