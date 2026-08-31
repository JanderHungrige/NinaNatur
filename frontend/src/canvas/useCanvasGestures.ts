/**
 * What a pointer gesture on the plan means right now.
 *
 * The plan understands five — pan, drag out a shape, sketch freehand, drop a
 * polygon corner, place a viewpoint — and the order they are tried in is the
 * whole content of this module. Without an order, one click both places a
 * viewpoint and drops a bed corner underneath it.
 */
import { useRef } from 'react';

import { snapPoint } from './snap';
import { type Point, type Viewport, panBy, toGarden } from './viewport';

/** Two decimals: a viewpoint is a place someone stands, not a survey mark. */
const round = (v: number): number => Math.round(v * 100) / 100;

interface Gesture {
  active: boolean;
  begin: (at: Point) => void;
  extend: (at: Point) => void;
  end: () => void;
}

interface Options {
  view: Viewport;
  setView: React.Dispatch<React.SetStateAction<Viewport>>;
  surface: React.RefObject<SVGSVGElement | null>;
  spacing: number;
  /** Polygon mode: clicks drop corners rather than starting a drag. */
  drawing: boolean;
  band: Gesture & { armed: boolean };
  stroke: Gesture & { armed: boolean };
  addVertex: (at: Point) => void;
  placing: boolean;
  onPlaceViewpoint?: ((x: number, y: number) => void) | undefined;
  onViewpointPlaced: () => void;
}

export function useCanvasGestures(options: Options) {
  /** Drag with the pointer to pan. Without it, zooming in strands the user. */
  const pan = useRef<{ x: number; y: number } | null>(null);

  /** Where a pointer landed, in garden metres. */
  const metres = (event: { clientX: number; clientY: number }): Point => {
    const rect = options.surface.current?.getBoundingClientRect();
    return toGarden(
      { x: event.clientX - (rect?.left ?? 0), y: event.clientY - (rect?.top ?? 0) },
      options.view,
    );
  };

  const onPointerDown = (event: React.PointerEvent<SVGSVGElement>) => {
    if (options.drawing) return;
    // A drawing gesture is never also a pan: one drag cannot both make a shape
    // and slide the ground out from under it.
    if (options.band.armed) {
      options.band.begin(metres(event));
      return;
    }
    if (options.stroke.armed) {
      options.stroke.begin(metres(event));
      return;
    }
    pan.current = { x: event.clientX, y: event.clientY };
  };

  const onPointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    if (options.band.active) {
      options.band.extend(metres(event));
      return;
    }
    if (options.stroke.active) {
      options.stroke.extend(metres(event));
      return;
    }
    const from = pan.current;
    if (from === null) return;
    pan.current = { x: event.clientX, y: event.clientY };
    options.setView((current) =>
      panBy(current, event.clientX - from.x, event.clientY - from.y),
    );
  };

  const endDrag = () => {
    if (options.band.active) {
      options.band.end();
      return;
    }
    if (options.stroke.active) {
      options.stroke.end();
      return;
    }
    pan.current = null;
  };

  /** A click, once the drags have had their say. */
  const onClick = (event: React.MouseEvent<SVGSVGElement>) => {
    if (options.placing && options.onPlaceViewpoint !== undefined) {
      const at = metres(event);
      options.onPlaceViewpoint(round(at.x), round(at.y));
      options.onViewpointPlaced();
      return;
    }
    if (!options.drawing) return;
    // Snapped in metres, after the transform: snapping pixels first would store
    // a different coordinate at every zoom level.
    options.addVertex(snapPoint(metres(event), options.spacing, { free: event.altKey }));
  };

  return { onPointerDown, onPointerMove, endDrag, onClick };
}
