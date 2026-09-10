"""Polite, cached HTTP for the ingest sources — and for the app's own outbound calls.

Every source here is a free public research API. Caching to disk means a rerun
of the pipeline costs zero requests, and the delay keeps a full-flora run from
looking like an attack.

Wave 20 (feature 5) gave every call a budget, because the same layer now serves
page loads, not only an ingest run somebody waits for:

- **Only what may change is retried.** A connection failure, a timeout or a 5xx
  may be gone in a second; a 4xx will not. Retrying a 404 cost 1+2+4 s of
  back-off for an answer that was never going to change.
- **Two timeouts, not one.** Connecting gets a few seconds; reading gets what
  the slowest honest answer needs. A caller on a page load passes its own.
- **An answer can be refused before it is cached.** Some services report a
  failure with a 200 — Overpass does, when it gives up on a query — and a cached
  failure is a permanent one.
- **The cache lives where it is told** (`NINANATUR_CACHE_DIR`, the volume in the
  container, so a roll no longer empties it) and forgets its oldest files past
  a cap (`NINANATUR_CACHE_MAX_MB`).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests

CACHE_DIR_ENV = "NINANATUR_CACHE_DIR"
CACHE_MAX_MB_ENV = "NINANATUR_CACHE_MAX_MB"
DEFAULT_CACHE_DIR = Path("data/cache")
#: Terrain windows are a quarter of a megabyte and a LoD2 tile tens of MB; this
#: holds a few hundred gardens' worth and is a rounding error on the host's disk.
DEFAULT_CACHE_MAX_MB = 500
#: When the cap is passed, prune down to this share of it, so the next few
#: writes do not each pay for a scan.
PRUNE_TO = 0.8

USER_AGENT = "NinaNatur-ingest/0.1 (open-data garden planning; contact: local dev)"
REQUEST_DELAY_S = 0.2
MAX_RETRIES = 3
#: (connect, read). Read covers Overpass's own 40 s query limit with a margin.
TIMEOUT: tuple[float, float] = (5.0, 45.0)


class HttpError(RuntimeError):
    """A request failed — refused by the server, or after exhausting retries."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        #: The HTTP status when the server answered; None for a network failure
        #: or an answer refused as incomplete.
        self.status = status


def cache_dir() -> Path:
    """Read per call, so a test — or a deployment — can point it elsewhere."""
    return Path(os.environ.get(CACHE_DIR_ENV) or DEFAULT_CACHE_DIR)


def _cache_path(url: str, params: dict[str, Any] | None) -> Path:
    key = hashlib.sha256(f"{url}|{sorted((params or {}).items())}".encode()).hexdigest()[:32]
    return cache_dir() / f"{key}.json"


def _keep(path: Path, write: Callable[[Path], object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write(path)
    _prune(path.parent)


def _prune(directory: Path) -> None:
    """Forget the oldest files once the cache is past its cap.

    Oldest by modification time, which for a write-once cache is when it was
    fetched. Everything here can be fetched again; nothing is lost but time.
    """
    cap = float(os.environ.get(CACHE_MAX_MB_ENV) or DEFAULT_CACHE_MAX_MB) * 1_000_000
    files = [(p.stat().st_mtime, p.stat().st_size, p) for p in directory.iterdir() if p.is_file()]
    total = sum(size for _mtime, size, _p in files)
    if total <= cap:
        return
    for _mtime, size, path in sorted(files, key=lambda f: f[0]):
        if total <= cap * PRUNE_TO:
            break
        path.unlink(missing_ok=True)
        total -= size


def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    use_cache: bool = True,
    timeout: tuple[float, float] = TIMEOUT,
    accept: Callable[[Any], bool] | None = None,
) -> Any:
    """GET a JSON document, served from disk cache when available.

    `accept` decides whether an answer is an answer. One it refuses raises
    `HttpError` and is never written to the cache.
    """
    path = _cache_path(url, params)
    if use_cache and path.exists():
        return json.loads(path.read_text())
    payload = _get(url, params, timeout).json()
    if accept is not None and not accept(payload):
        raise HttpError(f"GET {url} answered, but incompletely; not cached")
    if use_cache:
        _keep(path, lambda p: p.write_text(json.dumps(payload)))
    return payload


def get_text(url: str, params: dict[str, Any] | None = None, *, use_cache: bool = True) -> str:
    """GET a text document (CSV/TSV), served from disk cache when available."""
    path = _cache_path(url, params).with_suffix(".txt")
    if use_cache and path.exists():
        return path.read_text()
    text = _get(url, params, TIMEOUT).text
    if use_cache:
        _keep(path, lambda p: p.write_text(text))
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
    payload = _get(url, params, TIMEOUT).content
    if use_cache:
        _keep(path, lambda p: p.write_bytes(payload))
    return payload


def _get(
    url: str, params: dict[str, Any] | None, timeout: tuple[float, float],
) -> requests.Response:
    last: Exception | None = None
    for attempt in range(MAX_RETRIES):
        time.sleep(REQUEST_DELAY_S)
        try:
            response = requests.get(
                url, params=params, headers={"User-Agent": USER_AGENT}, timeout=timeout
            )
        except requests.RequestException as exc:  # noqa: PERF203 - retry needs the loop
            last = exc
        else:
            if response.status_code < 400:
                return response
            if response.status_code < 500:
                # Asking again gets the same answer. 429 included: it means
                # slow down, and three quick retries are the opposite.
                raise HttpError(f"GET {url} refused: {response.status_code}",
                                status=response.status_code)
            last = requests.HTTPError(f"{response.status_code} from {url}")
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
