/**
 * Provenance: NinaNatur, in the style of Draft Sketch
 *
 * The street network's outline, in his ink (doc 98). A street arrives from the
 * map as one way — a centreline and a width — so a junction is two bands lying
 * over each other, and an outline drawn per band runs straight through the
 * road beside it. Here every band's outline is drawn once and shown only
 * where no band covers it, which is what a road drawn by hand looks like: the
 * network's edge, and nothing across the junctions.
 */
import { useMemo } from 'react';

import type { Point } from '../../../canvas/viewport';
import type { PlanProps } from '../../types';
import { OVERLAYS } from '../generated/rules';
import type { Ink } from '../overlays';
import { mm, outline, width } from '../paths';

const STREET = 'street';
/** His wash's own ink is the street's: the same line every other surface has. */
const INK = (OVERLAYS['ds-grey'] ?? []).find((o): o is Ink => o.kind === 'ink');

/** The box round everything drawn, with room for the ink on the outside. */
function bounds(roads: readonly Point[][], margin: number) {
  const xs = roads.flat().map((p) => p.x);
  const ys = roads.flat().map((p) => -p.y);
  return {
    x: mm(Math.min(...xs) - margin), y: mm(Math.min(...ys) - margin),
    width: mm(Math.max(...xs) - Math.min(...xs) + 2 * margin),
    height: mm(Math.max(...ys) - Math.min(...ys) + 2 * margin),
  };
}

export function DraftSketchRoads({ shapes, metresPerPixel }: PlanProps) {
  // A street a hundred ways long is one path, drawn again only when the garden
  // or the scale changes — never on a drag frame.
  const network = useMemo(() => {
    const roads = shapes.filter((s) => s.kind === STREET).map((s) => s.points);
    if (roads.length === 0 || INK === undefined) return null;
    // The same line for the mask and for the ink, so a wobble cannot poke out
    // past the band it belongs to.
    return { d: roads.map((points) => outline(points, INK.wave, metresPerPixel)).join(''),
             box: bounds(roads, INK.width * 2) };
  }, [shapes, metresPerPixel]);
  if (network === null || INK === undefined) return null;
  const { d, box } = network;
  return (
    <g data-mark="roads">
      {/* By luminance, not alpha: what is painted black here is what is cut away. */}
      <mask id="ds-roads" maskUnits="userSpaceOnUse" {...box}>
        <rect {...box} fill="#ffffff" />
        <path d={d} fill="#000000" />
      </mask>
      {/* Twice his width: the half inside the road is masked away, and what is
          left outside is the line he draws. */}
      <path d={d} fill="none" stroke={INK.colour} strokeOpacity={INK.opacity}
            strokeWidth={width(INK.width * 2, metresPerPixel * 2)} strokeLinejoin="round"
            mask="url(#ds-roads)" />
    </g>
  );
}
