import type { MouseEvent } from 'react';

import {
  type Imagery,
  imageryUrl,
  type LatLon,
  latLonToPixel,
  type MapView,
  MAX_ZOOM,
  MIN_ZOOM,
  tileUrl,
  tilesFor,
} from '../map/tiles';
import type { Box, Surface } from '../map/useMapSurface';

interface Props {
  /** The measured surface and its drag, from `useMapSurface`. */
  surface: Surface;
  view: MapView;
  outline: LatLon[];
  imagery: Imagery | null;
  aerial: boolean;
  busy: boolean;
  zoom: number;
  onZoom: (by: number) => void;
  onAddCorner: (event: MouseEvent<HTMLDivElement>) => void;
  /** Set only by tests; otherwise the width is the layout's and is measured. */
  size: Box | undefined;
  /** How tall the map is drawn, in pixels. */
  height: number;
}

/**
 * The map itself: what it is drawn on, and what is drawn on it (doc 31).
 *
 * Everything here — the tiles, the aerial photo and the outline — is drawn in
 * the one box the surface measured, so a corner lands where the finger did.
 */
export function MapSurface({
  surface,
  view,
  outline,
  imagery,
  aerial,
  busy,
  zoom,
  onZoom,
  onAddCorner,
  size,
  height,
}: Props) {
  const box = surface.box;
  return (
    <>
      <div className="map-picker__zoom">
        <button
          type="button"
          aria-label="Herauszoomen"
          disabled={busy || zoom <= MIN_ZOOM}
          onClick={() => onZoom(-1)}
        >
          −
        </button>
        <button
          type="button"
          aria-label="Hineinzoomen"
          disabled={busy || zoom >= MAX_ZOOM}
          onClick={() => onZoom(1)}
        >
          +
        </button>
      </div>

      <div
        ref={surface.ref}
        data-testid="map-surface"
        className="map-picker__surface"
        // The height is ours; the width is the layout's to give and is measured.
        // A width set here would be a width the projection then believed (B1).
        style={size === undefined ? { height } : { width: size.widthPx, height: size.heightPx }}
        onClick={onAddCorner}
        onPointerDown={surface.onPointerDown}
        // Two fingers step the zoom (doc 31, B2); they are seen before the drag is.
        {...surface.pinch}
        // Otherwise the browser's own menu opens in the middle of a pan.
        onContextMenu={(event) => event.preventDefault()}
      >
        {aerial && imagery !== null ? (
          <img
            data-testid="map-aerial"
            className="map-picker__aerial"
            src={imageryUrl(imagery, view)}
            alt=""
            width={box.widthPx}
            height={box.heightPx}
          />
        ) : (
          <div data-testid="map-tiles" className="map-picker__tiles">
            {tilesFor(view).map((tile) => (
              <img
                key={`${tile.z}/${tile.x}/${tile.y}`}
                src={tileUrl(tile)}
                alt=""
                width={256}
                height={256}
                loading="lazy"
                style={{ left: tile.left, top: tile.top }}
              />
            ))}
          </div>
        )}
        <svg className="map-picker__outline" viewBox={`0 0 ${box.widthPx} ${box.heightPx}`}>
          {outline.length > 1 && (
            <polygon
              points={outline
                .map((p) => {
                  const px = latLonToPixel(p, view);
                  return `${px.x},${px.y}`;
                })
                .join(' ')}
            />
          )}
          {outline.map((p) => {
            const px = latLonToPixel(p, view);
            return <circle key={`${p.lat},${p.lon}`} cx={px.x} cy={px.y} r={4} />;
          })}
        </svg>
      </div>
    </>
  );
}
