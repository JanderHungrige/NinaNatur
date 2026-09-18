import type { ReactNode } from 'react';

import { centreOf, offset, overshoots, ticks, wobble } from '../../canvas/sketch';
import type { Point } from '../../canvas/viewport';
import type { DecoratedShape, Decoration } from '../types';
import type { Band, Centre, Ink, Overlay, Overshoot, Shadow, Ticks, Wave } from './overlays';

/*
 * His overlays drawn along one shape (doc 97): from its own outline, in garden
 * metres, bottom first. Shadows go under every shape; the rest over them.
 */

/** To the millimetre: a plan needs no finer, and a long street's path stays short. */
const mm = (value: number): string => String(Math.round(value * 1000) / 1000);

function ring(points: Point[]): string {
  return points.length === 0 ? '' : `M${points.map((p) => `${mm(p.x)},${mm(-p.y)}`).join('L')}Z`;
}

/** A wavering line as a pen draws it: curves through the midpoints, no corners. */
function smooth(points: Point[]): string {
  const at = (p: Point) => `${mm(p.x)},${mm(-p.y)}`;
  const middle = (a: Point, b: Point): Point => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });
  const last = points[points.length - 1]!;
  const curves = points.map((p, i) => `Q${at(p)} ${at(middle(p, points[(i + 1) % points.length]!))}`);
  return `M${at(middle(last, points[0]!))}${curves.join('')}Z`;
}

/** The outline as his wave draws it. A wave that would not move the line by a
 *  pixel is drawn straight: it could not be seen, and a curve every few
 *  centimetres round a hundred shapes is most of what the plan costs to draw. */
function outline(points: Point[], wave: Wave | null, metresPerPixel: number): string {
  if (wave === null || wave.amplitude < metresPerPixel || points.length < 3) return ring(points);
  return smooth(wobble(points, wave.amplitude, wave.period, wave.seed));
}

/** Marks closer together than this many pixels are a grey smear, and are left out. */
const APART_PX = 4;

/** His line at 1:250 is a hair at 1:2,000; it never gets thinner than a pixel. */
const width = (metres: number, metresPerPixel: number): string => mm(Math.max(metres, metresPerPixel));

function shadow(o: Shadow, points: Point[], mpp: number, key: string): ReactNode {
  return <path key={key} d={outline(offset(points, o.dx, o.dy), o.wave, mpp)}
               fill={o.colour} fillOpacity={o.opacity} />;
}

function ink(o: Ink, points: Point[], mpp: number, key: string): ReactNode {
  return <path key={key} d={outline(points, o.wave, mpp)} fill="none" stroke={o.colour}
               strokeOpacity={o.opacity} strokeWidth={width(o.width, mpp)}
               strokeLinejoin="round" strokeLinecap="round"
               strokeDasharray={o.dashes === null ? undefined : o.dashes.map(mm).join(' ')} />;
}

/** A rim inside the outline: a stroke twice as wide as the rim, clipped to the shape. */
function band(o: Band, points: Point[], mpp: number, key: string): ReactNode {
  const clip = `ds-clip-${key}`;
  return (
    <g key={key}>
      <clipPath id={clip}><path d={ring(points)} /></clipPath>
      <path d={outline(points, o.wave, mpp)} fill="none" stroke={o.colour}
            strokeOpacity={o.opacity} strokeWidth={mm(o.width + 2 * o.inset)}
            strokeLinejoin="round" clipPath={`url(#${clip})`} />
    </g>
  );
}

function overshoot(o: Overshoot, points: Point[], mpp: number, key: string): ReactNode {
  const d = overshoots(points, o.length)
    .map(([a, b]) => `M${mm(a.x)},${mm(-a.y)}L${mm(b.x)},${mm(-b.y)}`).join('');
  return <path key={key} d={d} fill="none" stroke={o.colour} strokeOpacity={o.opacity}
               strokeWidth={width(o.width, mpp)} strokeLinecap="round" />;
}

function tickMarks(o: Ticks, points: Point[], mpp: number, key: string): ReactNode {
  if (o.spacing < APART_PX * mpp) return null;
  const d = ticks(points, o.spacing, o.length, o.angle, o.inset)
    .map(([a, b]) => `M${mm(a.x)},${mm(-a.y)}L${mm(b.x)},${mm(-b.y)}`).join('');
  return <path key={key} d={d} fill="none" stroke={o.colour} strokeOpacity={o.opacity}
               strokeWidth={width(o.width, mpp)} strokeLinecap="round" />;
}

function centre(o: Centre, points: Point[], key: string): ReactNode {
  const c = centreOf(points);
  return <rect key={key} x={mm(c.x - o.width / 2)} y={mm(-c.y - o.height / 2)} width={mm(o.width)}
               height={mm(o.height)} fill={o.colour} fillOpacity={o.opacity} mask={`url(#${o.mask})`}
               transform={`rotate(${o.rotation} ${mm(c.x)} ${mm(-c.y)})`} />;
}

function drawn(o: Overlay, points: Point[], mpp: number, key: string): ReactNode {
  switch (o.kind) {
    case 'shadow': return shadow(o, points, mpp, key);
    case 'ink': return ink(o, points, mpp, key);
    case 'band': return band(o, points, mpp, key);
    case 'overshoot': return overshoot(o, points, mpp, key);
    case 'ticks': return tickMarks(o, points, mpp, key);
    case 'centre': return centre(o, points, key);
    case 'wash': return <path key={key} d={ring(points)} fill={o.fill} />;
  }
}

/** Everything his symbol draws along this shape, split into under and over. */
export function drawOverlays(shape: DecoratedShape, overlays: readonly Overlay[],
  metresPerPixel: number): Decoration {
  const under: ReactNode[] = [];
  const over: ReactNode[] = [];
  overlays.forEach((o, i) => {
    const mark = drawn(o, shape.points, metresPerPixel, `${shape.key}-${i}`);
    (o.kind === 'shadow' ? under : over).push(mark);
  });
  return { under, over };
}
