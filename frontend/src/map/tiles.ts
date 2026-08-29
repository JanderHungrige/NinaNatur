/**
 * Slippy-map tiles, computed rather than pulled in as a dependency.
 *
 * A tile layer is Web Mercator arithmetic and a grid of images; the project
 * already owns a metre-based viewport of its own, and a map library would bring
 * a second coordinate system with its own opinions. This file is the whole of
 * it, and it is testable without a browser.
 */

export interface LatLon {
  lat: number;
  lon: number;
}

export interface Pixel {
  x: number;
  y: number;
}

export interface MapView {
  lat: number;
  lon: number;
  zoom: number;
  widthPx: number;
  heightPx: number;
}

export interface Tile {
  z: number;
  x: number;
  y: number;
}

export const TILE_PX = 256;
export const MIN_ZOOM = 1;
/** What the OSM tile server serves. Asking beyond it is asking for 404s. */
export const MAX_ZOOM = 19;

/** The host the OSMF tile usage policy names. Anything else is another service
 *  with other terms — and the policy is explicit that this URL is the one. */
const TILE_HOST = 'https://tile.openstreetmap.org';

/** Required wherever the map is shown, by the licence and by the policy. */
export const ATTRIBUTION = '© OpenStreetMap-Mitwirkende';
export const ATTRIBUTION_URL = 'https://www.openstreetmap.org/copyright';

function clampZoom(zoom: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.round(zoom)));
}

/** World pixel coordinates at this zoom — the usual Web Mercator projection. */
function worldPixel(point: LatLon, zoom: number): Pixel {
  const scale = TILE_PX * 2 ** zoom;
  const sinLat = Math.sin((point.lat * Math.PI) / 180);
  return {
    x: ((point.lon + 180) / 360) * scale,
    y: (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * scale,
  };
}

function worldToLatLon(pixel: Pixel, zoom: number): LatLon {
  const scale = TILE_PX * 2 ** zoom;
  const n = Math.PI - (2 * Math.PI * pixel.y) / scale;
  return {
    lon: (pixel.x / scale) * 360 - 180,
    lat: (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n))),
  };
}

export function latLonToPixel(point: LatLon, view: MapView): Pixel {
  const zoom = clampZoom(view.zoom);
  const centre = worldPixel({ lat: view.lat, lon: view.lon }, zoom);
  const here = worldPixel(point, zoom);
  return {
    x: view.widthPx / 2 + (here.x - centre.x),
    y: view.heightPx / 2 + (here.y - centre.y),
  };
}

export function pixelToLatLon(pixel: Pixel, view: MapView): LatLon {
  const zoom = clampZoom(view.zoom);
  const centre = worldPixel({ lat: view.lat, lon: view.lon }, zoom);
  return worldToLatLon(
    {
      x: centre.x + (pixel.x - view.widthPx / 2),
      y: centre.y + (pixel.y - view.heightPx / 2),
    },
    zoom,
  );
}

/**
 * The tiles this window needs, and no more.
 *
 * Deliberately exactly the visible grid: the OSMF policy forbids bulk
 * downloading and prefetching outright, and a tile layer that helpfully warms
 * its neighbours is doing precisely that.
 */
export function tilesFor(view: MapView): Array<Tile & { left: number; top: number }> {
  const zoom = clampZoom(view.zoom);
  const span = 2 ** zoom;
  const centre = worldPixel({ lat: view.lat, lon: view.lon }, zoom);
  const originX = centre.x - view.widthPx / 2;
  const originY = centre.y - view.heightPx / 2;

  const firstX = Math.floor(originX / TILE_PX);
  const firstY = Math.floor(originY / TILE_PX);
  const lastX = Math.floor((originX + view.widthPx) / TILE_PX);
  const lastY = Math.floor((originY + view.heightPx) / TILE_PX);

  const tiles: Array<Tile & { left: number; top: number }> = [];
  for (let x = firstX; x <= lastX; x += 1) {
    for (let y = firstY; y <= lastY; y += 1) {
      // Wrap east-west, clamp north-south: there is no tile above the pole.
      const wrapped = ((x % span) + span) % span;
      if (y < 0 || y >= span) continue;
      tiles.push({
        z: zoom,
        x: wrapped,
        y,
        left: x * TILE_PX - originX,
        top: y * TILE_PX - originY,
      });
    }
  }
  return tiles;
}

export function tileUrl(tile: Tile): string {
  return `${TILE_HOST}/${tile.z}/${tile.x}/${tile.y}.png`;
}


export interface Imagery {
  url: string;
  layer: string;
  attribution: string;
}

/**
 * One WMS image covering the current window.
 *
 * A single GetMap for the visible extent rather than a tile grid: these are
 * state services sized for occasional use, and slicing their output into
 * dozens of requests per pan would be the same discourtesy the OSM tile policy
 * spells out.
 */
export function imageryUrl(imagery: Imagery, view: MapView): string {
  const nw = pixelToLatLon({ x: 0, y: 0 }, view);
  const se = pixelToLatLon({ x: view.widthPx, y: view.heightPx }, view);
  const params = new URLSearchParams({
    SERVICE: 'WMS',
    REQUEST: 'GetMap',
    VERSION: '1.3.0',
    // CRS:84 is lon/lat order, which sidesteps the axis-order trap that makes
    // EPSG:4326 in WMS 1.3.0 return a transposed image on half of all servers.
    CRS: 'CRS:84',
    LAYERS: imagery.layer,
    STYLES: '',
    FORMAT: 'image/png',
    WIDTH: String(Math.round(view.widthPx)),
    HEIGHT: String(Math.round(view.heightPx)),
    BBOX: `${nw.lon},${se.lat},${se.lon},${nw.lat}`,
  });
  return `${imagery.url}?${params.toString()}`;
}
