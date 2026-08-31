/**
 * Dragging a shape out at the size the hand asked for.
 *
 * The third gesture GardenCanvas understands, and the one Wave 10 was missing:
 * its palette stamped elements at a size somebody else chose, which is what
 * made them read as fixed.
 */
import { useRef, useState } from 'react';

import { type DrawnShape, type Tool, shapeFromDrag } from './shapes';
import type { Point } from './viewport';

interface Options {
  tool: Tool | null;
  onShape: (shape: DrawnShape) => void;
  onProblem: (message: string) => void;
}

export interface Band {
  from: Point;
  to: Point;
}

/** Tools that draw by dragging. Vieleck and Freihand are their own gestures. */
const DRAGGED: ReadonlySet<string> = new Set(['rect', 'circle', 'triangle']);

export function useShapeBand(options: Options) {
  const [band, setBand] = useState<Band | null>(null);
  // In a ref as well as in state, for the same reason the freehand stroke is:
  // pointer events outrun React's renders, and reading the band out of a render
  // closure on pointerup loses whatever the last move added.
  const current = useRef<Band | null>(null);

  const armed = options.tool !== null && DRAGGED.has(options.tool);

  const begin = (at: Point) => {
    current.current = { from: at, to: at };
    setBand(current.current);
  };

  const extend = (at: Point) => {
    if (current.current === null) return;
    current.current = { from: current.current.from, to: at };
    setBand(current.current);
  };

  const end = () => {
    const drawn = current.current;
    current.current = null;
    setBand(null);
    if (drawn === null || options.tool === null) return;
    const shape = shapeFromDrag(options.tool, drawn.from, drawn.to);
    // Said rather than silent: a drag that produced nothing otherwise looks
    // like a tool that does not work.
    if (shape === null) {
      options.onProblem('Zu klein — zieh die Form etwas größer auf.');
      return;
    }
    options.onShape(shape);
  };

  const cancel = () => {
    current.current = null;
    setBand(null);
  };

  return { band, armed, active: current.current !== null, begin, extend, end, cancel };
}
