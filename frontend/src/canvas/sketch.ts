import type { Point } from './viewport';

/*
 * The geometry a sketched outline is drawn with (doc 97): pure, seeded, and in
 * the garden's metres. A line that wavered differently on every render would
 * look like a fault, not a pen — so the same outline and seed always give the
 * same line, at every zoom.
 */

/** mulberry32: small, and the same numbers everywhere for the same seed. */
function random(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Points per period of a wave: a smooth line, and not a heavy one on a long street. */
const SAMPLES_PER_PERIOD = 4;

function edgeLengths(points: Point[]): number[] {
  return points.map((p, i) => {
    const q = points[(i + 1) % points.length]!;
    return Math.hypot(q.x - p.x, q.y - p.y);
  });
}

/**
 * An outline that wavers like a pen: every point moved off it at right angles,
 * by a smooth random amount of at most `amplitude` that changes its mind about
 * once a `period` — his "Random" waveform. The wave closes on itself, so a ring
 * ends where it began.
 */
export function wobble(points: Point[], amplitude: number, period: number, seed: number): Point[] {
  const lengths = edgeLengths(points);
  const perimeter = lengths.reduce((sum, l) => sum + l, 0);
  if (points.length < 2 || period <= 0 || perimeter === 0) return points.map((p) => ({ ...p }));
  const knots = Math.max(1, Math.round(perimeter / period));
  const next = random(seed);
  const heights = Array.from({ length: knots }, () => next() * 2 - 1);
  const wave = (s: number): number => {
    const u = (s / perimeter) * knots;
    const i = Math.floor(u) % knots;
    const eased = (1 - Math.cos((u - Math.floor(u)) * Math.PI)) / 2;
    return heights[i]! * (1 - eased) + heights[(i + 1) % knots]! * eased;
  };
  const step = period / SAMPLES_PER_PERIOD;
  const line: Point[] = [];
  let travelled = 0;
  points.forEach((a, i) => {
    const b = points[(i + 1) % points.length]!;
    const length = lengths[i]!;
    if (length === 0) return;
    const ux = (b.x - a.x) / length;
    const uy = (b.y - a.y) / length;
    const count = Math.max(1, Math.ceil(length / step));
    for (let k = 0; k < count; k += 1) {
      const along = (k / count) * length;
      const off = amplitude * wave(travelled + along);
      line.push({ x: a.x + ux * along + uy * off, y: a.y + uy * along - ux * off });
    }
    travelled += length;
  });
  return line;
}

/** Every edge carried on past both its ends by `length`: the corners a hand draws past. */
export function overshoots(points: Point[], length: number): [Point, Point][] {
  const marks: [Point, Point][] = [];
  points.forEach((a, i) => {
    const b = points[(i + 1) % points.length]!;
    const run = Math.hypot(b.x - a.x, b.y - a.y);
    if (run === 0) return;
    const ux = (b.x - a.x) / run;
    const uy = (b.y - a.y) / run;
    marks.push([{ x: a.x, y: a.y }, { x: a.x - ux * length, y: a.y - uy * length }]);
    marks.push([{ x: b.x, y: b.y }, { x: b.x + ux * length, y: b.y + uy * length }]);
  });
  return marks;
}

/** Twice the area the outline encloses, positive when it runs anticlockwise (y north). */
function turning(points: Point[]): number {
  return points.reduce((sum, a, i) => {
    const b = points[(i + 1) % points.length]!;
    return sum + a.x * b.y - b.x * a.y;
  }, 0);
}

/**
 * Short strokes every `spacing` along the outline, their middles `inset` inside
 * it, turned `angle` degrees from it: the marks his buildings carry along their
 * inner edge. Inside whichever way round the outline runs.
 */
export function ticks(points: Point[], spacing: number, length: number, angle: number,
  inset: number): [Point, Point][] {
  const marks: [Point, Point][] = [];
  if (spacing <= 0 || points.length < 3) return marks;
  const inward = turning(points) >= 0 ? 1 : -1;
  const turn = (angle * Math.PI) / 180;
  let next = spacing / 2;
  let travelled = 0;
  points.forEach((a, i) => {
    const b = points[(i + 1) % points.length]!;
    const run = Math.hypot(b.x - a.x, b.y - a.y);
    if (run === 0) return;
    const ux = (b.x - a.x) / run;
    const uy = (b.y - a.y) / run;
    const nx = -uy * inward;
    const ny = ux * inward;
    const dx = ((ux * Math.cos(turn) + nx * Math.sin(turn)) * length) / 2;
    const dy = ((uy * Math.cos(turn) + ny * Math.sin(turn)) * length) / 2;
    for (; next <= travelled + run; next += spacing) {
      const cx = a.x + ux * (next - travelled) + nx * inset;
      const cy = a.y + uy * (next - travelled) + ny * inset;
      marks.push([{ x: cx - dx, y: cy - dy }, { x: cx + dx, y: cy + dy }]);
    }
    travelled += run;
  });
  return marks;
}

/** The outline moved: a shadow where the drawing's light puts it. */
export function offset(points: Point[], dx: number, dy: number): Point[] {
  return points.map((p) => ({ x: p.x + dx, y: p.y + dy }));
}

/** Where a shape's middle is: its centroid by area, or — with no area — its mean. */
export function centreOf(points: Point[]): Point {
  let area = 0;
  let cx = 0;
  let cy = 0;
  points.forEach((a, i) => {
    const b = points[(i + 1) % points.length]!;
    const cross = a.x * b.y - b.x * a.y;
    area += cross;
    cx += (a.x + b.x) * cross;
    cy += (a.y + b.y) * cross;
  });
  if (Math.abs(area) < 1e-12) {
    const n = Math.max(1, points.length);
    return { x: points.reduce((s, p) => s + p.x, 0) / n, y: points.reduce((s, p) => s + p.y, 0) / n };
  }
  return { x: cx / (3 * area), y: cy / (3 * area) };
}
