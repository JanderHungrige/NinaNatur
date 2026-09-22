import { useState } from 'react';
import type { RefObject } from 'react';

import type { LightMap } from '../api/client';
import { atPoint, bandFor } from '../components/SunMap';
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
 * A readout rather than a `<title>` on the map: the map is a few paths with
 * `pointer-events: none`, which is what lets a click reach the bed underneath
 * it. Turning that on for a tooltip would make the wash swallow every selection
 * on the plan.
 *
 * Its state lives in `SunReadout`, which is all a pointer move re-renders.
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
    const garden = toGarden({ x: left, y: top }, view);
    const at = atPoint(map, garden.x, garden.y);
    if (at === null) return setReadout(null);
    // "Dach" first, because a roof's hours answer a different question from the
    // ground's and a reader who missed that would take it for the bed below.
    // Then what the sky adds (doc 118): the hours to expect once the climate's
    // cloud is counted, and how much of the sky the spot sees.
    const reading = [
      `${at.hours.toFixed(1)} h · ${bandFor(at.hours)}`,
      at.expected === null ? null : `erwartbar ${at.expected.toFixed(1)} h`,
      at.sky === null ? null : `sieht ${Math.round(at.sky * 100)} % des Himmels`,
    ].filter((part) => part !== null).join(' · ');
    return setReadout({ left, top, text: at.onARoof ? `Dach · ${reading}` : reading });
  };

  return { readout, read, clear: () => setReadout(null) };
}
