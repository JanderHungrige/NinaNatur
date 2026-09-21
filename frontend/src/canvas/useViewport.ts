/**
 * The window onto the garden: how big the surface is, and where the wheel
 * takes it.
 *
 * The measuring effect exists because of something found by looking at the
 * running app rather than by reasoning: a box that has not been laid out
 * measures zero.
 *
 * What is measured is the **stage** the drawing sits in, never the drawing. The
 * drawing's height used to follow its viewBox, and the viewBox followed the
 * drawing's measured height — one short measurement and the plan stayed a 12 px
 * strip until a reload (doc 86). The stage takes its height from the page, so
 * nothing drawn inside it can change what is measured.
 */
import { useEffect, useRef, useState } from 'react';

import { useMoving } from './useMoving';
import { type Viewport, measuredView, zoomAt } from './viewport';

const DEFAULT_SIZE = { widthPx: 800, heightPx: 600 };
const ZOOM_STEP = 1.6;

/** Per pixel of wheel travel. A mouse notch is about 100 px: some 1.3 times. */
const WHEEL_SPEED = 0.0025;
/** A trackpad pinch arrives as small ctrl-wheel deltas, many a second. */
const PINCH_SPEED = 0.01;
/** However large one event claims to be, it moves the view by at most this. */
const MAX_STEP = 2;

/** Safari's own pinch, which TypeScript's DOM types do not describe. */
interface GestureEvent extends UIEvent {
  scale: number;
  clientX: number;
  clientY: number;
}

/** How far one wheel event zooms: more than 1 is out, as a positive delta is. */
export function wheelFactor(event: WheelEvent, pageHeight: number): number {
  const lines = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? pageHeight : 1;
  const px = event.deltaY * lines;
  const factor = Math.exp(px * (event.ctrlKey ? PINCH_SPEED : WHEEL_SPEED));
  return Math.min(MAX_STEP, Math.max(1 / MAX_STEP, factor));
}

export function useViewport(size?: { widthPx: number; heightPx: number } | undefined) {
  const [view, setView] = useState<Viewport>({
    centreX: 0,
    centreY: 0,
    spanM: 40,
    ...(size ?? DEFAULT_SIZE),
  });
  const surface = useRef<SVGSVGElement | null>(null);
  const stage = useRef<HTMLDivElement | null>(null);
  const moving = useMoving(surface);

  useEffect(() => {
    if (size !== undefined) return undefined;
    const element = stage.current;
    if (element === null || typeof ResizeObserver === 'undefined') return undefined;
    const measure = () => {
      const box = element.getBoundingClientRect();
      setView((current) => measuredView(current, box));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [size]);

  /**
   * Wheel zoom, anchored on the pointer so the garden stays where it was.
   *
   * A plain wheel zooms, as on any map (the owner's check, 2026-09-21, #4). It
   * once needed Ctrl or Cmd, because a plain wheel swallowed the page's
   * scroll. Since the workspace became a full-height app (doc 86), nothing
   * scrolls behind the plan. Each event zooms in proportion to how far it
   * scrolled. A fixed 1.6 per event sent a trackpad pinch, which arrives as
   * dozens of tiny ctrl-wheel events a second, to the limit at once. Safari
   * sends its pinch as gesture events instead, and zoomed the page with them.
   */
  useEffect(() => {
    const element = surface.current;
    if (element === null) return undefined;
    const zoomTo = (clientX: number, clientY: number, factor: number) => {
      const rect = element.getBoundingClientRect();
      moving.pulse();
      setView((current) =>
        zoomAt(current, { x: clientX - rect.left, y: clientY - rect.top }, factor),
      );
    };
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      zoomTo(event.clientX, event.clientY, wheelFactor(event, element.clientHeight));
    };
    let lastScale = 1;
    const onGestureStart = (event: Event) => {
      event.preventDefault();
      lastScale = 1;
    };
    const onGestureChange = (event: Event) => {
      event.preventDefault();
      const gesture = event as GestureEvent;
      if (!(gesture.scale > 0)) return;
      zoomTo(gesture.clientX, gesture.clientY, lastScale / gesture.scale);
      lastScale = gesture.scale;
    };
    element.addEventListener('wheel', onWheel, { passive: false });
    element.addEventListener('gesturestart', onGestureStart, { passive: false });
    element.addEventListener('gesturechange', onGestureChange, { passive: false });
    return () => {
      element.removeEventListener('wheel', onWheel);
      element.removeEventListener('gesturestart', onGestureStart);
      element.removeEventListener('gesturechange', onGestureChange);
    };
  }, [moving]);

  /** The buttons, in words rather than in a factor: a caller passing 1.6 for
   *  "in" is a caller who will eventually pass it for "out". */
  const zoom = (direction: 'in' | 'out') =>
    setView((current) =>
      zoomAt(
        current,
        { x: current.widthPx / 2, y: current.heightPx / 2 },
        direction === 'in' ? 1 / ZOOM_STEP : ZOOM_STEP,
      ),
    );

  return { view, setView, surface, stage, zoom, moving };
}
