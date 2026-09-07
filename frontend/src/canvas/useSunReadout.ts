import { useState } from 'react';
import type { RefObject } from 'react';

import type { LightMap } from '../api/client';
import { bandFor, hoursAt } from '../components/SunMap';
import { type Viewport, toGarden } from './viewport';

export interface Readout {
  /** Pixels from the drawing's top left, not the page's. */
  left: number;
  top: number;
  text: string;
}

/**
 * What the sun map says under the pointer.
 *
 * A readout rather than a `<title>` on every cell: the map is up to six hundred
 * rects with `pointer-events: none`, which is what lets a click reach the bed
 * underneath it. Turning that on for a tooltip would make the wash swallow
 * every selection on the plan.
 *
 * Its own hook because `GardenCanvas` is long, and because this is the same
 * shape as every other pointer concern already living in `canvas/`.
 */
export function useSunReadout(
  map: LightMap | undefined,
  view: Viewport,
  surface: RefObject<SVGSVGElement | null>,
) {
  const [readout, setReadout] = useState<Readout | null>(null);

  const read = (event: { clientX: number; clientY: number }): void => {
    const box = surface.current?.getBoundingClientRect();
    if (map === undefined || box === undefined) return setReadout(null);
    const left = event.clientX - box.left;
    const top = event.clientY - box.top;
    const at = toGarden({ x: left, y: top }, view);
    const hours = hoursAt(map, at.x, at.y);
    // Undefined is off the grid and says nothing. Null is a cell with a roof
    // over it, which is a different answer and worth giving.
    if (hours === undefined) return setReadout(null);
    return setReadout({
      left,
      top,
      text:
        hours === null
          ? 'Dach — kein Boden'
          : `${hours.toFixed(1)} h · ${bandFor(hours)}`,
    });
  };

  return { readout, read, clear: () => setReadout(null) };
}
