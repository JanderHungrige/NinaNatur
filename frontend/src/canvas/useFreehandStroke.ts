/**
 * A freehand stroke, from the first press to the shape it becomes.
 *
 * Split out of GardenCanvas with the handle drag, for the same reason: the
 * component was carrying every gesture the plan understands, and they are read
 * one at a time.
 */
import { useRef, useState } from 'react';

import { tidy } from './freehand';
import type { Point } from './viewport';

interface Options {
  view: { spanM: number; widthPx: number };
  onShape: (polygon: number[][]) => void;
  onProblem: (message: string) => void;
  onDone: () => void;
}

export function useFreehandStroke(options: Options) {
  const [stroke, setStroke] = useState<Point[] | null>(null);
  // The points live in a ref and are mirrored into state for drawing. The ref
  // is what pointerup reads: state read from a render closure is one render
  // behind whenever events arrive faster than React re-renders, and losing the
  // last points of a stroke that way would be invisible until it wasn't.
  const points = useRef<Point[] | null>(null);

  const begin = (at: Point) => {
    points.current = [at];
    setStroke(points.current);
  };

  const extend = (at: Point) => {
    if (points.current === null) return;
    points.current = [...points.current, at];
    setStroke(points.current);
  };

  const end = () => {
    const drawn = points.current;
    points.current = null;
    setStroke(null);
    if (drawn === null) return;
    options.onDone();
    const perPixel = options.view.spanM / options.view.widthPx;
    // Two pixels, but never finer than 10 cm however far the user has zoomed
    // in. Without the floor a close-up scribble stores a corner every few
    // millimetres — detail no gardener plants to, carried by every later
    // light computation. The floor matches the centimetre the outline is
    // rounded to.
    const shape = tidy(drawn, {
      tolerance: Math.max(0.1, perPixel * 2),
      closeWithin: Math.max(0.5, perPixel * 12),
    });
    if (shape === null) {
      options.onProblem('Der Umriss spannt keine Fläche auf — zieh eine geschlossene Form.');
      return;
    }
    options.onShape(shape.map((p) => [p.x, p.y]));
  };

  return { stroke, active: points.current !== null, begin, extend, end };
}
