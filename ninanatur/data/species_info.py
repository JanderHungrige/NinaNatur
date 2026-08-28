"""Descriptions and photographs from Wikipedia.

An API, not a crawler: the REST summary endpoint returns exactly what a panel
needs and redirects the scientific name to the German article, so
`Achillea millefolium` arrives as *Gemeine Schafgarbe* without any name mapping.

Cached on the volume rather than shipped in the catalogue. This content is
derived, refreshable and per-deployment — the same shape as a garden, not the
same shape as plant data.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from urllib.parse import quote

from ninanatur.ingest.http import get_json

# Wikipedia text is CC-BY-SA 4.0. Attribution and a link back are conditions of
# use, not decoration, and a cached copy does not become ours.
LICENCE = "CC-BY-SA-4.0"

SUMMARY_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
LANGUAGES = ("de", "en")

# A hit is stable for a long time; a miss is not. Remembering "no article"
# forever would freeze a gap Wikipedia may close next week, while re-asking on
# every view would hammer a free service for a known-absent page.
HIT_TTL_DAYS = 90
MISS_TTL_DAYS = 14


class SummaryClient(Protocol):
    """The one call this module needs — narrow, so tests can substitute it."""

    def summary(self, title: str, language: str) -> dict[str, Any] | None: ...


class WikipediaClient:
    """Live Wikipedia REST summaries."""

    def summary(self, title: str, language: str) -> dict[str, Any] | None:
        url = SUMMARY_URL.format(lang=language, title=quote(title.replace(" ", "_")))
        result = get_json(url)
        return result if isinstance(result, dict) else None


@dataclass(frozen=True)
class SpeciesInfo:
    """A description and photo, with the credit that has to travel with them."""

    taxon_id: int
    title: str
    extract: str
    thumbnail_url: str | None
    page_url: str
    language: str
    licence: str = LICENCE


def _now() -> datetime:
    return datetime.now(UTC)


def _is_fresh(fetched_at: str, found: bool) -> bool:
    try:
        stamp = datetime.fromisoformat(fetched_at)
    except ValueError:
        return False
    ttl = timedelta(days=HIT_TTL_DAYS if found else MISS_TTL_DAYS)
    return _now() - stamp < ttl


def _parse(payload: dict[str, Any], language: str, taxon_id: int) -> SpeciesInfo | None:
    """Turn a summary response into an entry, or None when there is nothing to show."""
    extract = str(payload.get("extract") or "").strip()
    title = str(payload.get("title") or "").strip()
    if not extract or not title:
        # A stub page with a title and no text is not information.
        return None
    thumbnail = payload.get("thumbnail")
    urls = payload.get("content_urls")
    page = ""
    if isinstance(urls, dict):
        desktop = urls.get("desktop")
        if isinstance(desktop, dict):
            page = str(desktop.get("page") or "")
    return SpeciesInfo(
        taxon_id=taxon_id,
        title=title,
        extract=extract,
        thumbnail_url=str(thumbnail["source"]) if isinstance(thumbnail, dict) else None,
        page_url=page or f"https://{language}.wikipedia.org/wiki/{quote(title)}",
        language=language,
    )


def _cached(conn: sqlite3.Connection, taxon_id: int) -> tuple[SpeciesInfo | None, bool]:
    """Return (entry, usable). `usable` is False when there is nothing fresh."""
    row = conn.execute(
        "SELECT * FROM species_info WHERE taxon_id = ?", (taxon_id,)
    ).fetchone()
    if row is None or not _is_fresh(row["fetched_at"], bool(row["found"])):
        return None, False
    if not row["found"]:
        return None, True  # a fresh, remembered miss
    return (
        SpeciesInfo(
            taxon_id=taxon_id,
            title=row["title"],
            extract=row["extract"],
            thumbnail_url=row["thumbnail_url"],
            page_url=row["page_url"],
            language=row["language"],
        ),
        True,
    )


def _store(conn: sqlite3.Connection, taxon_id: int, info: SpeciesInfo | None) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO species_info
            (taxon_id, title, extract, thumbnail_url, page_url, language, found, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            taxon_id,
            info.title if info else None,
            info.extract if info else None,
            info.thumbnail_url if info else None,
            info.page_url if info else None,
            info.language if info else None,
            int(info is not None),
            _now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()


def species_info(
    conn: sqlite3.Connection,
    taxon_id: int,
    client: SummaryClient | None = None,
) -> SpeciesInfo | None:
    """A description and photo for one species, or None when there is none.

    German first, English as a fallback, and the result says which. A failure to
    reach Wikipedia returns None rather than raising: a plant list must not break
    because an external service is down.
    """
    cached, usable = _cached(conn, taxon_id)
    if usable:
        return cached

    row = conn.execute(
        "SELECT canonical_name FROM taxon WHERE taxon_id = ?", (taxon_id,)
    ).fetchone()
    if row is None:
        return None

    lookup = client or WikipediaClient()
    for language in LANGUAGES:
        try:
            payload = lookup.summary(str(row["canonical_name"]), language)
        except Exception:  # noqa: BLE001 - any failure degrades to "no info"
            return None
        if payload is None:
            continue
        info = _parse(payload, language, taxon_id)
        if info is not None:
            _store(conn, taxon_id, info)
            return info

    _store(conn, taxon_id, None)
    return None
