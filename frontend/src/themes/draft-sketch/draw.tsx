import type { ReactNode } from 'react';

import { halfWidth } from '../../canvas/along';
import { centreOf, inset, offset, overshoots, scaled, sweep, ticks } from '../../canvas/sketch';
import type { Point } from '../../canvas/viewport';
import type { DecoratedShape, Decoration } from '../types';
import type {
  Band, Centre, Inner, Ink, Joins, Overlay, Overshoot, RoofLines, Shadow, Ticks, Wave,
} from './overlays';
import { disc, mm, outline, ring, stroke, width } from './paths';

/*
 * His overlays drawn along one shape (docs 97, 98): from its own outline, in
 * garden metres, bottom first. A shape's shadow goes beneath the shape itself;
 * the rest over every shape.
 */

/** Marks closer together than this many pixels are a grey smear, and are left out. */
const APART_PX = 4;

/**
 * His marks are sized for the shapes he drew them round. On a smaller one —
 * a shrub a metre across under his Tree 2 — a wave or a tick of his size is
 * a scribble over the whole of it, so none is let grow past a share of the
 * shape's own radius: an adaptation, and one that leaves his lawns, houses
 * and trees exactly as they were.
 */
const WAVE_SHARE = 0.125;
const TICK_SHARE = 0.35;

function radiusOf(points: Point[]): number {
  let twice = 0;
  points.forEach((a, i) => {
    const b = points[(i + 1) % points.length]!;
    twice += a.x * b.y - b.x * a.y;
  });
  return Math.sqrt(Math.abs(twice) / 2 / Math.PI);
}

function capped(wave: Wave | null, radius: number): Wave | null {
  if (wave === null || wave.amplitude <= WAVE_SHARE * radius) return wave;
  const shrink = (WAVE_SHARE * radius) / wave.amplitude;
  return { ...wave, amplitude: wave.amplitude * shrink, period: wave.period * shrink };
}

/**
 * His drop shadow, thrown where the sun actually throws it (doc 99). The server
 * gives each standing thing its offset at the drawing's one moment; a thing
 * that casts none is drawn without a shadow rather than with a stylish guess.
 * A bed's edge shadow is its own depth and says so.
 */
function shadow(o: Shadow, shape: DecoratedShape, mpp: number, key: string): ReactNode {
  const points = shape.points;
  const at = o.edge === true ? { x: o.dx, y: o.dy } : shape.shadow;
  if (at === null) return null;
  // A bed's edge is the shape moved a little; a thing that stands up hides the
  // ground all the way over, so its shadow is the shape swept (doc 99).
  const cast = o.edge === true ? offset(points, at.x, at.y) : sweep(points, at.x, at.y);
  const wave = o.edge === true ? capped(o.wave, radiusOf(points)) : null;
  // Drawn beneath its shape, among the targets: it must never be one itself.
  return <path key={key} data-mark="shadow" className="canvas__shadow" pointerEvents="none"
               aria-hidden="true" d={outline(cast, wave, mpp)}
               fill={o.colour} fillOpacity={o.opacity} />;
}

/**
 * The corner a road turns (doc 98). A way is a rectangle, so two of them meeting
 * at an angle leave the outside of the bend open — a wedge at a shallow angle, a
 * notch a metre wide at a sharp one. A disc of the band's own width at each end
 * of its centreline is the round join the rectangles do not have, and it is
 * drawn beneath the band, where it can fill a corner without covering anything.
 */
function joins(o: Joins, shape: DecoratedShape, key: string): ReactNode {
  const line = shape.line;
  if (line === null || line.length < 2) return null;
  const radius = (shape.bandWidth ?? 2 * halfWidth(shape.points)) / 2;
  if (radius <= 0) return null;
  const d = disc(line[0]!, radius) + disc(line[line.length - 1]!, radius);
  return <path key={key} data-mark="joins" d={d} fill={o.fill} />;
}

function ink(o: Ink, points: Point[], mpp: number, key: string): ReactNode {
  const around = scaled(points, o.scale ?? 1);
  const d = outline(around, capped(o.wave, radiusOf(around)), mpp);
  return <path key={key} data-mark="ink" d={d} fill="none" stroke={o.colour}
               strokeOpacity={o.opacity} strokeWidth={width(o.width, mpp)}
               strokeLinejoin="round" strokeLinecap="round"
               strokeDasharray={o.dashes === null ? undefined : o.dashes.map(mm).join(' ')} />;
}

/** A rim inside the outline: a stroke twice as wide as the rim, clipped to the shape. */
function band(o: Band, points: Point[], mpp: number, key: string): ReactNode {
  const clip = `ds-clip-${key}`;
  return (
    <g key={key} data-mark="band">
      <clipPath id={clip}><path d={ring(points)} /></clipPath>
      <path d={outline(points, o.wave, mpp)} fill="none" stroke={o.colour}
            strokeOpacity={o.opacity} strokeWidth={mm(o.width + 2 * o.inset)}
            strokeLinejoin="round" clipPath={`url(#${clip})`} />
    </g>
  );
}

function segments(marks: [Point, Point][]): string {
  return marks.map(([a, b]) => `M${mm(a.x)},${mm(-a.y)}L${mm(b.x)},${mm(-b.y)}`).join('');
}

function overshoot(o: Overshoot, points: Point[], mpp: number, key: string): ReactNode {
  return <path key={key} data-mark="overshoot" d={segments(overshoots(points, o.length))}
               fill="none" stroke={o.colour} strokeOpacity={o.opacity}
               strokeWidth={width(o.width, mpp)} strokeLinecap="round" />;
}

function tickMarks(o: Ticks, points: Point[], mpp: number, key: string): ReactNode {
  if (o.spacing < APART_PX * mpp) return null;
  const around = scaled(points, o.scale ?? 1);
  const longest = Math.max(1, ...(o.sizes ?? [1]));
  const length = Math.min(o.length, (TICK_SHARE * radiusOf(around)) / longest);
  const marks = ticks(around, o.spacing, length, o.angle, o.inset,
    { sizes: o.sizes, facing: o.facing });
  return <path key={key} data-mark="ticks" d={segments(marks)} fill="none" stroke={o.colour}
               strokeOpacity={o.opacity} strokeWidth={width(o.width, mpp)} strokeLinecap="round" />;
}

/** A pent roof's one line is its upper edge, on the wall's own line where it
 *  cannot be seen; an arrow from its middle into the roof says which way it
 *  falls — drawn from the server's line and the outline, nothing else. */
function fall(edge: [Point, Point], points: Point[]): string {
  const [a, b] = edge;
  const from = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  const c = centreOf(points);
  const tail = { x: from.x + (c.x - from.x) * 0.25, y: from.y + (c.y - from.y) * 0.25 };
  const tip = { x: from.x + (c.x - from.x) * 1.1, y: from.y + (c.y - from.y) * 1.1 };
  const back = Math.hypot(tip.x - tail.x, tip.y - tail.y) * 0.3;
  const heading = Math.atan2(tip.y - tail.y, tip.x - tail.x);
  const barb = (turn: number) => ({ x: tip.x - back * Math.cos(heading + turn),
                                    y: tip.y - back * Math.sin(heading + turn) });
  return segments([[tail, tip], [barb(0.45), tip], [barb(-0.45), tip]]);
}

function roof(o: RoofLines, shape: DecoratedShape, mpp: number, key: string): ReactNode {
  const lines = shape.roofLines;
  if (lines.length === 0) return null;
  const arrow = shape.roof === 'pent' && lines.length === 1 ? fall(lines[0]!, shape.points) : '';
  const d = lines.map((line) => stroke(line, o.wave, mpp)).join('') + arrow;
  return <path key={key} data-mark="roof" d={d} fill="none" stroke={o.colour}
               strokeOpacity={o.opacity} strokeWidth={width(o.width, mpp)} strokeLinecap="round" />;
}

function inner(o: Inner, points: Point[], mpp: number, key: string): ReactNode {
  return <path key={key} data-mark="inner" d={outline(inset(points, o.inset), o.wave, mpp)} fill="none"
               stroke={o.colour} strokeOpacity={o.opacity} strokeWidth={width(o.width, mpp)}
               strokeLinejoin="round" />;
}

/** An image of his smaller than this many pixels is a speck: drawn as the mark it
 *  is, not through a mask of its own (a layer per tree, for four pixels). */
const IMAGE_PX = 8;

function centre(o: Centre, points: Point[], mpp: number, key: string): ReactNode {
  const c = centreOf(points);
  if (Math.max(o.width, o.height) / mpp < IMAGE_PX) {
    // His centre mark, as his style sheet shows it drawn: an upright cross.
    const arm = Math.min(o.width, o.height) / 2;
    const d = segments([[{ x: c.x - arm, y: c.y }, { x: c.x + arm, y: c.y }],
                        [{ x: c.x, y: c.y - arm }, { x: c.x, y: c.y + arm }]]);
    return <path key={key} data-mark="centre" d={d} fill="none" stroke={o.colour}
                 strokeOpacity={o.opacity} strokeWidth={width(o.height * 0.2, mpp)} strokeLinecap="round" />;
  }
  return <rect key={key} data-mark="centre" x={mm(c.x - o.width / 2)} y={mm(-c.y - o.height / 2)}
               width={mm(o.width)} height={mm(o.height)} fill={o.colour} fillOpacity={o.opacity}
               mask={`url(#${o.mask})`}
               transform={`rotate(${o.rotation} ${mm(c.x)} ${mm(-c.y)})`} />;
}

function drawn(o: Overlay, shape: DecoratedShape, mpp: number, key: string): ReactNode {
  const points = shape.points;
  switch (o.kind) {
    case 'shadow': return shadow(o, shape, mpp, key);
    case 'joins': return joins(o, shape, key);
    case 'ink': return ink(o, points, mpp, key);
    case 'band': return band(o, points, mpp, key);
    case 'overshoot': return overshoot(o, points, mpp, key);
    case 'ticks': return tickMarks(o, points, mpp, key);
    case 'centre': return centre(o, points, mpp, key);
    case 'wash': return <path key={key} data-mark="wash" d={ring(points)} fill={o.fill} />;
    case 'roof': return roof(o, shape, mpp, key);
    case 'inner': return inner(o, points, mpp, key);
    // Laid along a line, not round an outline: drawAlong's.
    default: return null;
  }
}

/** Everything drawn round this shape's outline, split into under and over. */
export function drawOverlays(shape: DecoratedShape, overlays: readonly Overlay[],
  metresPerPixel: number): Decoration {
  const under: ReactNode[] = [];
  const over: ReactNode[] = [];
  overlays.forEach((o, i) => {
    const mark = drawn(o, shape, metresPerPixel, `${shape.key}-${i}`);
    // A shadow and a road's corner go under the shape; everything else over it.
    const beneath = o.kind === 'shadow' || o.kind === 'joins';
    if (mark !== null) (beneath ? under : over).push(mark);
  });
  return { under, over };
}
