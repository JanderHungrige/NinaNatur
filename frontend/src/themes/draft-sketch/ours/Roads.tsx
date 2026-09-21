/**
 * Provenance: NinaNatur, in the style of Draft Sketch
 *
 * The street network's outline, in his ink (doc 98). A street arrives from the
 * map as one way — a centreline and a width — so a junction is two bands lying
 * over each other, and an outline drawn per band runs straight through the
 * road beside it. Here every band's outline is drawn once and shown only
 * where no band covers it, which is what a road drawn by hand looks like: the
 * network's edge, and nothing across the junctions.
 *
 * Nor across a house. The outline is drawn over every shape, so a house the map
 * put on the road had the road's line running through it, over its roof (the
 * owner, 2026-09-21). What is built is cut out of the line as the bands are.
 */
import { useMemo } from 'react';

import { halfWidth } from '../../../canvas/along';
import type { Point } from '../../../canvas/viewport';
import { isBuilt } from '../../../kinds';
import type { DecoratedShape, PlanProps } from '../../types';
import { OVERLAYS } from '../generated/rules';
import type { Ink } from '../overlays';
import { disc, inkWidth, mm, outline, ring } from '../paths';

const STREET = 'street';
/** A way that ends on another way's edge puts the two boundaries on top of each
 *  other, and a hairline of ink shows through the seam — a line across a road,
 *  which is the very thing this draws away. The mask is grown by most of a
 *  pixel so it swallows them. */
const SEAM_PX = 0.75;
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

/** Every built outline, turned the same way round: overlapping ones then add up
 *  in the mask instead of cancelling where they overlap. */
function builtOver(shapes: readonly DecoratedShape[]): string {
  return shapes.filter((s) => isBuilt(s.kind) && s.points.length >= 3).map((s) => {
    const twice = s.points.reduce((sum, p, i) => {
      const q = s.points[(i + 1) % s.points.length]!;
      return sum + p.x * q.y - q.x * p.y;
    }, 0);
    return ring(twice < 0 ? [...s.points].reverse() : s.points);
  }).join('');
}

export function DraftSketchRoads({ shapes, metresPerPixel }: PlanProps) {
  // A street a hundred ways long is one path, drawn again only when the garden
  // or the scale changes — never on a drag frame.
  const network = useMemo(() => {
    const streets = shapes.filter((s) => s.kind === STREET);
    const roads = streets.map((s) => s.points);
    if (roads.length === 0 || INK === undefined) return null;
    // Where a way ends, the road turns: the same disc the band's wash is
    // rounded with, so the line and the grey agree at every corner.
    const radii = streets.map((s) => (s.bandWidth ?? 2 * halfWidth(s.points)) / 2);
    const corners = streets.flatMap((s, i) => {
      const line = s.line;
      const radius = radii[i]!;
      if (line === null || line.length < 2 || radius <= 0) return [];
      return [disc(line[0]!, radius), disc(line[line.length - 1]!, radius)];
    }).join('');
    // The same line for the mask and for the ink, so a wobble cannot poke out
    // past the band it belongs to.
    const grow = metresPerPixel * SEAM_PX;
    // His width as it is drawn at this scale: capped when zoomed in (paths.ts).
    const ink = inkWidth(INK.width, metresPerPixel);
    return { d: roads.map((points) => outline(points, INK.wave, metresPerPixel)).join(''),
             corners, built: builtOver(shapes),
             // The discs reach a radius past the band's own end: the box, and so
             // the mask, must hold them, or a road's rounded end has no line.
             box: bounds(roads, ink * 2 + grow * 2 + Math.max(0, ...radii)), grow, ink };
  }, [shapes, metresPerPixel]);
  if (network === null || INK === undefined) return null;
  const { d, corners, built, box, grow, ink } = network;
  return (
    <g data-mark="roads">
      {/* By luminance, not alpha: what is painted black here is what is cut away.
          The corners are a path of their own — in one path with the bands, a
          disc that winds the other way cancels against the band it sits in and
          punches a hole in the mask, which lets the ink through inside the
          road. */}
      <mask id="ds-roads" maskUnits="userSpaceOnUse" {...box}>
        <rect {...box} fill="#ffffff" />
        <path d={d} fill="#000000" stroke="#000000" strokeWidth={mm(grow * 2)}
              strokeLinejoin="round" />
        <path d={corners} fill="#000000" stroke="#000000" strokeWidth={mm(grow * 2)} />
        {built !== '' && <path data-mark="built" d={built} fill="#000000" />}
      </mask>
      {/* Twice his width, and twice the grown mask's on top: everything inside
          the roads is masked away, and what is left outside is his line. */}
      <path d={d + corners} fill="none" stroke={INK.colour} strokeOpacity={INK.opacity}
            strokeWidth={mm(Math.max((ink + grow) * 2, (metresPerPixel + grow) * 2))}
            strokeLinejoin="round" mask="url(#ds-roads)" />
    </g>
  );
}
