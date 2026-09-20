"""A tile that arrives in an archive — Wave 25, feature 1 (doc 103).

Doc 102 called six states "index states" because their tiles were thought to
need a portal index before an address existed. Read properly, most of them
needed no such thing: Thüringen names every one of its 16,945 tiles from the
grid and Sachsen every one of its 19,881, and what actually stood in the way
was that each tile arrives wrapped in a zip. This takes the wrapper off. It is
not another tier — the name the registry computes is the archive's name, and
the grid is unchanged.

What is inside was read rather than assumed, on **2026-09-20**:

- **Thüringen** packs the GeoTIFF beside the same heights as a 29 MB `.xyz`
  and a `.meta`; its CityGML beside a `.txt`.
- **Sachsen** adds a world file, a GDAL sidecar and a currency CSV.
- **Brandenburg** adds an HTML metadata page.
- **Berlin** writes CityGML as `.xml`, where everyone else writes `.gml`.
- **Baden-Württemberg** puts *four one-kilometre tiles* in one two-kilometre
  archive, inside a folder, next to the licence as a PDF.

So: members are chosen by extension, sorted by name — which for Baden-
Württemberg is the grid's own order — and a member is measured before it is
read, never after.
"""
from __future__ import annotations

import io
import shutil
import zipfile
from pathlib import Path

#: The largest member this will unpack. Thüringen's CityGML is 36 MB of XML
#: and its laser member about 110 MB; four hundred is generous for those and
#: still refuses an archive that would be the whole of memory. A caller that
#: knows its product is smaller passes its own.
MAX_MEMBER_BYTES = 400_000_000


class ArchiveError(ValueError):
    """An archive this will not guess at."""


def named(data: bytes, *, want: tuple[str, ...],
          max_member_bytes: int = MAX_MEMBER_BYTES) -> list[tuple[str, bytes]]:
    """Every member whose name ends in one of `want`, with its name, in name
    order.

    The name matters for Baden-Württemberg, whose archive holds four tiles of
    its own grid; everywhere else there is one member and the name is noise.
    """
    wanted = tuple(suffix.lower() for suffix in want)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            picked = sorted(
                (entry for entry in archive.infolist()
                 if not entry.is_dir() and entry.filename.lower().endswith(wanted)),
                key=lambda entry: entry.filename)
            if not picked:
                raise ArchiveError(
                    f"no {' or '.join(wanted)} in the archive, only "
                    f"{sorted(e.filename.rsplit('.', 1)[-1] for e in archive.infolist())}")
            for entry in picked:
                # The declared size, before a byte is decompressed: the same
                # order as the TIFF reader's header check (Wave 20, feature 8).
                if entry.file_size > max_member_bytes:
                    raise ArchiveError(
                        f"{entry.filename} is too large: {entry.file_size} bytes")
            return [(entry.filename, archive.read(entry)) for entry in picked]
    except ArchiveError:
        raise
    # Deflate64 raises NotImplementedError, which is how Berlin's laser bundles
    # would surface; a portal's maintenance page raises BadZipFile.
    except (zipfile.BadZipFile, NotImplementedError, OSError, RuntimeError) as broken:
        raise ArchiveError(f"not an archive this can read: {broken}") from broken


def extract(archive: Path, *, want: tuple[str, ...], out: Path,
            max_member_bytes: int = MAX_MEMBER_BYTES) -> Path:
    """Write the wanted member out beside its archive, and say where it went.

    The point cloud reader takes a path and streams from it, because the
    largest tile in the country is 445 MB and holding one is the whole budget
    (doc 107). So this streams too: the member is copied through a megabyte at
    a time rather than read into memory and written back out.

    Written whole or not at all, like everything else on the volume — half a
    point cloud that looks like a point cloud is a day of somebody's life.
    """
    if out.exists():
        return out
    wanted = tuple(suffix.lower() for suffix in want)
    try:
        with zipfile.ZipFile(archive) as bundle:
            entry = next((found for found in sorted(bundle.infolist(),
                                                    key=lambda found: found.filename)
                          if not found.is_dir()
                          and found.filename.lower().endswith(wanted)), None)
            if entry is None:
                raise ArchiveError(f"no {' or '.join(wanted)} in {archive.name}")
            if entry.file_size > max_member_bytes:
                raise ArchiveError(f"{entry.filename} is too large: {entry.file_size} bytes")
            out.parent.mkdir(parents=True, exist_ok=True)
            part = out.with_suffix(f"{out.suffix}.part")
            with bundle.open(entry) as inside, part.open("wb") as sink:
                shutil.copyfileobj(inside, sink, length=1 << 20)
            part.replace(out)
    except ArchiveError:
        raise
    except (zipfile.BadZipFile, NotImplementedError, OSError, RuntimeError) as broken:
        raise ArchiveError(f"could not take {archive.name} apart: {broken}") from broken
    return out


def unpack(data: bytes, *, want: tuple[str, ...],
           max_member_bytes: int = MAX_MEMBER_BYTES) -> list[bytes]:
    """The same, for the callers that only want what is in the members."""
    return [body for _name, body in named(data, want=want,
                                          max_member_bytes=max_member_bytes)]


__all__ = ["MAX_MEMBER_BYTES", "ArchiveError", "extract", "named", "unpack"]
