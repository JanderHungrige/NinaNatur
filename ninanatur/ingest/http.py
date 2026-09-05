"""Polite, cached HTTP for the ingest sources.

Every source here is a free public research API. Caching to disk means a rerun
of the pipeline costs zero requests, and the delay keeps a full-flora run from
looking like an attack.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests

CACHE_DIR = Path("data/cache")
USER_AGENT = "NinaNatur-ingest/0.1 (open-data garden planning; contact: local dev)"
REQUEST_DELAY_S = 0.2
MAX_RETRIES = 3


class HttpError(RuntimeError):
    """A request failed after exhausting retries."""


def _cache_path(url: str, params: dict[str, Any] | None) -> Path:
    key = hashlib.sha256(f"{url}|{sorted((params or {}).items())}".encode()).hexdigest()[:32]
    return CACHE_DIR / f"{key}.json"


def get_json(url: str, params: dict[str, Any] | None = None, *, use_cache: bool = True) -> Any:
    """GET a JSON document, served from disk cache when available."""
    path = _cache_path(url, params)
    if use_cache and path.exists():
        return json.loads(path.read_text())
    payload = _get(url, params).json()
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
    return payload


def get_text(url: str, params: dict[str, Any] | None = None, *, use_cache: bool = True) -> str:
    """GET a text document (CSV/TSV), served from disk cache when available."""
    path = _cache_path(url, params).with_suffix(".txt")
    if use_cache and path.exists():
        return path.read_text()
    text = _get(url, params).text
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return text


def get_bytes(url: str, params: dict[str, Any] | None = None, *, use_cache: bool = True) -> bytes:
    """GET a binary document, served from disk cache when available.

    The coverage services answer a request for one garden's ground with a
    quarter of a megabyte of GeoTIFF. Terrain does not change, so the second
    garden in the same street should cost nothing — and the state surveying
    offices are public infrastructure nobody is paying us to hammer.
    """
    path = _cache_path(url, params).with_suffix(".bin")
    if use_cache and path.exists():
        return path.read_bytes()
    payload = _get(url, params).content
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return payload


def _get(url: str, params: dict[str, Any] | None) -> requests.Response:
    last: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(REQUEST_DELAY_S)
            response = requests.get(
                url, params=params, headers={"User-Agent": USER_AGENT}, timeout=60
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:  # noqa: PERF203 - retry needs the loop
            last = exc
            time.sleep(2**attempt)
    raise HttpError(f"GET {url} failed after {MAX_RETRIES} attempts: {last}") from last


def download(url: str, dest: Path) -> Path:
    """Download a binary file once; subsequent calls reuse the local copy."""
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=300, stream=True) as r:
        r.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 16):
                fh.write(chunk)
    return dest
