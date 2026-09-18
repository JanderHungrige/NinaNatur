import type { Point } from './viewport';

/*
 * The geometry a sketched outline is drawn with (doc 97): pure, seeded, and in
 * the garden's metres. A line that wavered differently on every render would
 * look like a fault, not a pen — so the same outline and seed always give the
 * same line, at every zoom.
 */

/** mulberry32: small, and the same numbers everywhere for the same seed. */
export function seeded(seed: number): () => number {
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

/** A smooth random wander between -1 and 1 over `total` metres, changing its
 *  mind `knots` times; closed, it ends where it began. */
function wander(total: number, knots: number, seed: number, closed: boolean): (s: number) => number {
  const next = seeded(seed);
  const heights = Array.from({ length: closed ? knots : knots + 1 }, () => next() * 2 - 1);
  return (s) => {
    const u = (s / total) * knots;
    const i = Math.min(Math.floor(u), closed ? Number.MAX_SAFE_INTEGER : knots - 1);
    const eased = (1 - Math.cos((u - i) * Math.PI)) / 2;
    const [a, b] = closed ? [i % knots, (i + 1) % knots] : [i, i + 1];
    return heights[a]! * (1 - eased) + heights[b]! * eased;
  };
}

function waver(points: Point[], amplitude: number, period: number, seed: number,
  closed: boolean, minStep: number): Point[] {
  const edges = closed ? points.length : points.length - 1;
  const lengths = edgeLengths(points).slice(0, Math.max(0, edges));
  const total = lengths.reduce((sum, l) => sum + l, 0);
  if (points.length < 2 || period <= 0 || total === 0) return points.map((p) => ({ ...p }));
  const wave = wander(total, Math.max(1, Math.round(total / period)), seed, closed);
  const step = Math.max(period / SAMPLES_PER_PERIOD, minStep);
  const line: Point[] = [];
  let travelled = 0;
  lengths.forEach((length, i) => {
    const a = points[i]!;
    const b = points[(i + 1) % points.length]!;
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
    if (!closed && i === lengths.length - 1) {
      const off = amplitude * wave(total);
      line.push({ x: b.x + uy * off, y: b.y - ux * off });
    }
  });
  return line;
}

/**
 * An outline that wavers like a pen: every point moved off it at right angles,
 * by a smooth random amount of at most `amplitude` that changes its mind about
 * once a `period` — his "Random" waveform. The wave closes on itself, so a ring
 * ends where it began. Points are never closer than `minStep`: the drawing's
 * pixels, where a wave's own spacing would put several in one.
 */
export function wobble(points: Point[], amplitude: number, period: number, seed: number,
  minStep = 0): Point[] {
  return waver(points, amplitude, period, seed, true, minStep);
}

/** A line that wavers as an outline does, from its first point to its last. */
export function wobbleLine(line: Point[], amplitude: number, period: number, seed: number,
  minStep = 0): Point[] {
  return waver(line, amplitude, period, seed, false, minStep);
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
export interface TickOptions {
  /** Lengths as shares of `length`, one tick after another, round again. */
  sizes?: readonly number[] | undefined;
  /** Only the edges whose outside faces this way: the side in shade. */
  facing?: Point | undefined;
}

export function ticks(points: Point[], spacing: number, length: number, angle: number,
  inset: number, { sizes, facing }: TickOptions = {}): [Point, Point][] {
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
    const shaded = facing === undefined || -(nx * facing.x + ny * facing.y) > 0;
    for (; next <= travelled + run; next += spacing) {
      const share = sizes === undefined || sizes.length === 0 ? 1 : sizes[marks.length % sizes.length]!;
      const dx = ((ux * Math.cos(turn) + nx * Math.sin(turn)) * length * share) / 2;
      const dy = ((uy * Math.cos(turn) + ny * Math.sin(turn)) * length * share) / 2;
      const cx = a.x + ux * (next - travelled) + nx * inset;
      const cy = a.y + uy * (next - travelled) + ny * inset;
      if (shaded) marks.push([{ x: cx - dx, y: cy - dy }, { x: cx + dx, y: cy + dy }]);
    }
    travelled += run;
  });
  return marks;
}

/** The outline drawn again `factor` times as large, about its middle. */
export function scaled(points: Point[], factor: number): Point[] {
  if (factor === 1) return points;
  const c = centreOf(points);
  return points.map((p) => ({ x: c.x + (p.x - c.x) * factor, y: c.y + (p.y - c.y) * factor }));
}

/** The outline moved `distance` inside itself, its corners mitred: a raised
 *  bed's second edge. Inside whichever way round the outline runs. */
export function inset(points: Point[], distance: number): Point[] {
  const n = points.length;
  if (n < 3 || distance === 0) return points.map((p) => ({ ...p }));
  const inward = turning(points) >= 0 ? 1 : -1;
  const normal = (a: Point, b: Point): Point => {
    const run = Math.hypot(b.x - a.x, b.y - a.y) || 1;
    return { x: (-(b.y - a.y) / run) * inward, y: ((b.x - a.x) / run) * inward };
  };
  return points.map((p, i) => {
    const before = normal(points[(i - 1 + n) % n]!, p);
    const after = normal(p, points[(i + 1) % n]!);
    const mitre = { x: before.x + after.x, y: before.y + after.y };
    const along = before.x * mitre.x + before.y * mitre.y;
    if (Math.abs(along) < 1e-9) return { x: p.x + before.x * distance, y: p.y + before.y * distance };
    return { x: p.x + (mitre.x * distance) / along, y: p.y + (mitre.y * distance) / along };
  });
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
