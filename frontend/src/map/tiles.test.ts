import { describe, expect, it } from 'vitest';

import {
  MAX_ZOOM,
  MIN_ZOOM,
  type MapView,
  latLonToPixel,
  pixelToLatLon,
  tileUrl,
  tilesFor,
} from './tiles';

const VIEW: MapView = { lat: 52.4055, lon: 13.21, zoom: 18, widthPx: 640, heightPx: 400 };

describe('the Web Mercator transform', () => {
  it('puts the view centre in the middle of the window', () => {
    const p = latLonToPixel({ lat: VIEW.lat, lon: VIEW.lon }, VIEW);
    expect(p.x).toBeCloseTo(320, 6);
    expect(p.y).toBeCloseTo(200, 6);
  });

  it('puts north up', () => {
    // A sign error here mirrors the map against the garden it produces.
    expect(latLonToPixel({ lat: VIEW.lat + 0.001, lon: VIEW.lon }, VIEW).y).toBeLessThan(200);
  });

  it('puts east right', () => {
    expect(latLonToPixel({ lat: VIEW.lat, lon: VIEW.lon + 0.001 }, VIEW).x).toBeGreaterThan(320);
  });

  it('round-trips a point', () => {
    const point = { lat: 52.4061, lon: 13.2117 };
    const back = pixelToLatLon(latLonToPixel(point, VIEW), VIEW);
    expect(back.lat).toBeCloseTo(point.lat, 9);
    expect(back.lon).toBeCloseTo(point.lon, 9);
  });

  it('shows more ground at a lower zoom', () => {
    const near = pixelToLatLon({ x: 640, y: 200 }, VIEW).lon - VIEW.lon;
    const far = pixelToLatLon({ x: 640, y: 200 }, { ...VIEW, zoom: 15 }).lon - VIEW.lon;
    expect(far).toBeGreaterThan(near);
  });
});

describe('the tiles to fetch', () => {
  it('covers the window', () => {
    const tiles = tilesFor(VIEW);
    expect(tiles.length).toBeGreaterThan(0);
    for (const t of tiles) {
      expect(t.z).toBe(18);
      expect(Number.isInteger(t.x)).toBe(true);
    }
  });

  it('asks for no more than the window needs', () => {
    // Bulk fetching is what the OSMF tile policy forbids outright. A window of
    // 640x400 at 256 px tiles is at most 4x3 tiles plus a border.
    expect(tilesFor(VIEW).length).toBeLessThanOrEqual(20);
  });

  it('never asks for a tile outside the world', () => {
    const edge = tilesFor({ ...VIEW, lat: 85, lon: 179.9, zoom: 3 });
    const span = 2 ** 3;
    for (const t of edge) {
      expect(t.x).toBeGreaterThanOrEqual(0);
      expect(t.x).toBeLessThan(span);
      expect(t.y).toBeGreaterThanOrEqual(0);
      expect(t.y).toBeLessThan(span);
    }
  });

  it('clamps the zoom to what the tile server serves', () => {
    expect(tilesFor({ ...VIEW, zoom: 30 })[0]?.z).toBe(MAX_ZOOM);
    expect(tilesFor({ ...VIEW, zoom: -1 })[0]?.z).toBe(MIN_ZOOM);
  });

  it('uses the URL the tile policy names', () => {
    // The policy names this host explicitly; anything else is a different
    // service with different terms.
    expect(tileUrl({ z: 18, x: 1, y: 2 })).toBe('https://tile.openstreetmap.org/18/1/2.png');
  });
});
