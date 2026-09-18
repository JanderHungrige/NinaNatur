import type { ReactNode } from 'react';

import { centreline, halfWidth, parallel, stations } from '../../canvas/along';
import { seeded } from '../../canvas/sketch';
import type { Point } from '../../canvas/viewport';
import type { DecoratedShape, Decoration } from '../types';
import { IMAGE } from './generated/symbols';
import type { LineBoxes, LineEnds, LineInk, LineMarks, LineOverlay } from './overlays';
import { mm, ring, stroke, width } from './paths';

/*
 * His line symbols laid along an element's line (doc 98) — its own line when
 * it is drawn as one, else its outline's long axis.
 *
 * A fence gets his Wood Fence as he drew it. A wall gets his Brick Wall
 * fitted: his two faces stand 0.7 m apart at 1:250 and a garden wall is 0.3 m
 * thick, so the wall's own outline is his faces, every sideways distance of
 * his is scaled to the wall's width, and all of it is clipped to the wall —
 * adapted from Draft Sketch.
 */

const RAD = 180 / Math.PI;

/** An image of his smaller than this many pixels is not drawn as his picture:
 *  at that size it is a speck, and every one is an element to build. A fence's
 *  posts keep their outline without it (see `boxes`). */
const IMAGE_PX = 8;

const faint = (o: LineMarks, metresPerPixel: number): boolean =>
  (Math.max(o.width, o.height) * Math.max(1, ...(o.sizes ?? [1]))) / metresPerPixel < IMAGE_PX;

interface Placed {
  mask: string;
  colour: string;
  opacity: number;
  width: number;
  height: number;
}

/** One of his images at a point, turned `degrees` anticlockwise (y north). */
function image(o: Placed, at: Point, degrees: number, size: number, key: string,
  mark: string): ReactNode {
  const w = o.width * size;
  const h = o.height * size;
  return <rect key={key} data-mark={mark} x={mm(at.x - w / 2)} y={mm(-at.y - h / 2)}
               width={mm(w)} height={mm(h)} fill={o.colour} fillOpacity={o.opacity}
               mask={`url(#${o.mask})`}
               transform={`rotate(${mm(-degrees)} ${mm(at.x)} ${mm(-at.y)})`} />;
}

function ink(o: LineInk, line: Point[], fit: number, mpp: number, key: string): ReactNode {
  const run = parallel(line, o.offset * fit);
  return <path key={key} data-mark={o.kind} d={stroke(run, o.wave, mpp)} fill="none"
               stroke={o.colour} strokeOpacity={o.opacity} strokeWidth={width(o.width, mpp)}
               strokeLinecap="round" strokeLinejoin="round" />;
}

/**
 * Every mark of one of his layers along the line, through one mask: his
 * image at each place, and his colour over all of them at once. A mask per
 * mark was a layer of its own per fence post and per mortar joint, and most
 * of what a street of fences cost to draw.
 */
function marks(o: LineMarks, line: Point[], fit: number, key: string): ReactNode {
  const href = IMAGE[o.image];
  const stray = seeded(o.seed);
  const placed = stations(line, o.spacing, o.start).map((station, i) => {
    const size = o.sizes === undefined ? 1 : o.sizes[i % o.sizes.length]!;
    const off = (o.jitter ?? 0) * fit * (stray() * 2 - 1);
    return { at: { x: station.at.x - Math.sin(station.angle) * off,
                   y: station.at.y + Math.cos(station.angle) * off },
             turn: station.angle * RAD + o.rotation, w: o.width * size, h: o.height * size };
  });
  if (href === undefined || placed.length === 0) return null;
  const reach = Math.max(...placed.map((p) => Math.hypot(p.w, p.h) / 2));
  const xs = placed.map((p) => p.at.x);
  const ys = placed.map((p) => -p.at.y);
  const box = { x: mm(Math.min(...xs) - reach), y: mm(Math.min(...ys) - reach),
                width: mm(Math.max(...xs) - Math.min(...xs) + 2 * reach),
                height: mm(Math.max(...ys) - Math.min(...ys) + 2 * reach) };
  const id = `ds-marks-${key}`;
  return (
    <g key={key} data-mark={o.kind}>
      <mask id={id} maskUnits="userSpaceOnUse" {...box} style={{ maskType: 'alpha' }}>
        {placed.map((p, i) => (
          <image key={i} href={href} x={mm(p.at.x - p.w / 2)} y={mm(-p.at.y - p.h / 2)}
                 width={mm(p.w)} height={mm(p.h)} preserveAspectRatio="none"
                 transform={`rotate(${mm(-p.turn)} ${mm(p.at.x)} ${mm(-p.at.y)})`} />
        ))}
      </mask>
      <rect {...box} fill={o.colour} fillOpacity={o.opacity} mask={`url(#${id})`} />
    </g>
  );
}

/** His posts: every square of a fence in one path, turned with the line. When
 *  his picture of a post is too small to draw, the square is outlined itself. */
function boxes(o: LineBoxes, line: Point[], outlined: boolean, mpp: number, key: string): ReactNode {
  const half = o.size / 2;
  const d = stations(line, o.spacing, o.start).map(({ at, angle }) => {
    const [c, s] = [Math.cos(angle) * half, Math.sin(angle) * half];
    const corners = [[c - s, s + c], [-c - s, -s + c], [-c + s, -s - c], [c + s, s - c]];
    return `M${corners.map(([dx, dy]) => `${mm(at.x + dx!)},${mm(-(at.y + dy!))}`).join('L')}Z`;
  }).join('');
  return <path key={key} data-mark={o.kind} d={d} fill={o.colour} fillOpacity={o.opacity}
               stroke={outlined ? '#000000' : 'none'} strokeWidth={width(0.03, mpp)} />;
}

function ends(o: LineEnds, line: Point[], key: string): ReactNode {
  const first = line[0]!;
  const last = line[line.length - 1]!;
  const heading = (a: Point, b: Point) => Math.atan2(b.y - a.y, b.x - a.x) * RAD;
  return [
    image(o, first, heading(first, line[1] ?? first) + o.rotation, 1, `${key}-0`, o.kind),
    image(o, last, heading(line[line.length - 2] ?? last, last) + o.rotation, 1, `${key}-1`,
      o.kind),
  ];
}

/** His line symbol along this shape; `fitted` lays it on a wall's own faces. */
export function drawAlong(shape: DecoratedShape, overlays: readonly LineOverlay[],
  metresPerPixel: number, fitted: boolean): Decoration {
  const line = shape.line ?? centreline(shape.points);
  if (line.length < 2) return { under: [], over: [] };
  const offsets = overlays.map((o) => (o.kind === 'line-ink' ? Math.abs(o.offset) : 0));
  const widest = Math.max(0, ...offsets);
  const fit = fitted && widest > 0 ? halfWidth(shape.points) / widest : 1;
  const specks = overlays.some((o) => o.kind === 'line-marks' && faint(o, metresPerPixel));
  const drawn = overlays.map((o, i) => {
    const key = `${shape.key}-along-${i}`;
    switch (o.kind) {
      // Fitted, his faces are the wall's own outline, drawn with it.
      case 'line-ink': return fitted && o.offset !== 0 ? null : ink(o, line, fit, metresPerPixel, key);
      case 'line-marks': return faint(o, metresPerPixel) ? null : marks(o, line, fit, key);
      case 'line-boxes': return boxes(o, line, specks, metresPerPixel, key);
      case 'line-ends': return ends(o, line, key);
    }
  });
  if (!fitted) return { under: [], over: drawn };
  const clip = `ds-clip-${shape.key}-along`;
  return {
    under: [],
    over: [
      <g key={clip} data-mark="fitted">
        <clipPath id={clip}><path d={ring(shape.points)} /></clipPath>
        <g clipPath={`url(#${clip})`}>{drawn}</g>
      </g>,
    ],
  };
}
