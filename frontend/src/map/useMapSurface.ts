import { type PointerEvent as ReactPointerEvent, type RefObject, useEffect, useRef, useState } from 'react';

import { type MapView, pixelToLatLon } from './tiles';

export interface Box {
  widthPx: number;
  heightPx: number;
}

/** A pointer that moved less than this tapped; more than this dragged the map. */
const TAP_PX = 6;

interface Options {
  /** The size to draw at until the surface has been measured. */
  fallback: Box;
  /** Overrides the measurement; tests pass it because jsdom lays nothing out. */
  size: Box | undefined;
  /** Whether the surface is on the page at all — it appears with the map. */
  shown: boolean;
  /** Where the map looks now; null before an address is chosen. */
  look: { lat: number; lon: number; zoom: number } | null;
  /** Where it should look after a drag. */
  onLook: (at: { lat: number; lon: number }) => void;
}

export interface Surface {
  /** Read only here; React fills it. Typed as the element's own ref, which is
   *  what a `ref` prop takes. */
  ref: RefObject<HTMLDivElement>;
  /** The size everything on the map is drawn at. */
  box: Box;
  onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
  /** Whether the gesture just ended moved the map, so the click that follows it
   *  belongs to the pan rather than setting a corner. */
  dragged: () => boolean;
}

/**
 * The map's surface: how big it really is, and dragging it (doc 31, B1).
 *
 * The size is measured rather than assumed. The projection, the tiles, the
 * aerial photo and the outline are all drawn in this one box, and a fixed size
 * lied to all four on any window narrower than it: on a phone the surface is
 * 259 px where 640 was assumed, and a tap set a corner 77 px from the finger.
 *
 * Dragging is the right mouse button, because the left one is already how a
 * corner is set — and a finger, which has no buttons, so the gesture is told
 * apart by distance instead.
 */
export function useMapSurface({ fallback, size, shown, look, onLook }: Options): Surface {
  const ref = useRef<HTMLDivElement | null>(null);
  const [measured, setMeasured] = useState<Box | null>(null);
  const [panning, setPanning] = useState(false);
  const from = useRef<{ x: number; y: number; lat: number; lon: number; zoom: number } | null>(null);
  const moved = useRef(false);
  // Read during a drag, so a new handler on every render re-subscribes nothing.
  const latest = useRef(onLook);
  latest.current = onLook;

  const box = size ?? measured ?? fallback;

  useEffect(() => {
    if (size !== undefined || !shown) return undefined;
    const element = ref.current;
    if (element === null || typeof ResizeObserver === 'undefined') return undefined;
    const measure = () => {
      const seen = element.getBoundingClientRect();
      const next = { widthPx: Math.round(seen.width), heightPx: Math.round(seen.height) };
      // A surface with no size yet is not a measurement; the fallback holds.
      if (next.widthPx === 0 || next.heightPx === 0) return;
      setMeasured((was) =>
        was?.widthPx === next.widthPx && was?.heightPx === next.heightPx ? was : next,
      );
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [size, shown]);

  useEffect(() => {
    if (!panning) return undefined;
    const onMove = (event: PointerEvent) => {
      const grabbed = from.current;
      if (grabbed === null) return;
      const dx = event.clientX - grabbed.x;
      const dy = event.clientY - grabbed.y;
      // Below the threshold the gesture may still be a tap, and the map holds still.
      if (!moved.current && Math.hypot(dx, dy) <= TAP_PX) return;
      moved.current = true;
      // Through the projection rather than by scaling degrees: a degree of
      // longitude is not a degree of latitude, and at 52° it is not close.
      const at: MapView = { lat: grabbed.lat, lon: grabbed.lon, zoom: grabbed.zoom, ...box };
      latest.current(pixelToLatLon({ x: box.widthPx / 2 - dx, y: box.heightPx / 2 - dy }, at));
    };
    const done = () => {
      from.current = null;
      setPanning(false);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', done);
    // A touch the system takes away — a call, a gesture from the edge — ends it too.
    window.addEventListener('pointercancel', done);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', done);
      window.removeEventListener('pointercancel', done);
    };
  }, [panning, box.widthPx, box.heightPx]);

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    const byTouch = event.pointerType !== 'mouse';
    // A new gesture: whatever the last one was, its click has been and gone.
    moved.current = false;
    if (look === null || (!byTouch && event.button !== 2)) return;
    // Not for a finger: preventing a touch's default takes with it the click
    // that follows, and that click is how a tap sets its corner.
    if (!byTouch) event.preventDefault();
    from.current = { x: event.clientX, y: event.clientY, ...look };
    setPanning(true);
  };

  return { ref, box, onPointerDown, dragged: () => moved.current };
}
