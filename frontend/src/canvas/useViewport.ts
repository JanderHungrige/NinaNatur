/**
 * The window onto the garden: how big the surface is, and where the wheel
 * takes it.
 *
 * Both effects here exist because of something found by looking at the running
 * app rather than by reasoning: an SVG that has not been laid out measures
 * zero, and a plain wheel over the canvas swallowed every page scroll.
 */
import { useEffect, useRef, useState } from 'react';

import { type Viewport, zoomAt } from './viewport';

const DEFAULT_SIZE = { widthPx: 800, heightPx: 600 };
const ZOOM_STEP = 1.6;

export function useViewport(size?: { widthPx: number; heightPx: number } | undefined) {
  const [view, setView] = useState<Viewport>({
    centreX: 0,
    centreY: 0,
    spanM: 40,
    ...(size ?? DEFAULT_SIZE),
  });
  const surface = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (size !== undefined) return undefined;
    const element = surface.current;
    if (element === null || typeof ResizeObserver === 'undefined') return undefined;
    const measure = () => {
      const rect = element.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return;
      setView((current) =>
        current.widthPx === rect.width && current.heightPx === rect.height
          ? current
          : { ...current, widthPx: rect.width, heightPx: rect.height },
      );
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [size]);

  /**
   * Wheel zoom, anchored on the pointer so the garden stays where it was — but
   * only with Ctrl or Cmd held.
   *
   * A plain wheel over the canvas used to zoom, which meant the page could not
   * be scrolled past the plan at all: every scroll gesture was swallowed and
   * the view zoomed to its limit instead. Found by loading the page and letting
   * it scroll. Ctrl+wheel is also the browser's own zoom gesture, so it is the
   * one people already reach for, and the buttons remain the real control.
   */
  useEffect(() => {
    const element = surface.current;
    if (element === null) return undefined;
    const onWheel = (event: WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return; // let the page scroll
      event.preventDefault();
      const rect = element.getBoundingClientRect();
      setView((current) =>
        zoomAt(
          current,
          { x: event.clientX - rect.left, y: event.clientY - rect.top },
          event.deltaY > 0 ? ZOOM_STEP : 1 / ZOOM_STEP,
        ),
      );
    };
    element.addEventListener('wheel', onWheel, { passive: false });
    return () => element.removeEventListener('wheel', onWheel);
  }, []);

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

  return { view, setView, surface, zoom };
}
