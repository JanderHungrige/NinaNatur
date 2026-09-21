import type { Point } from './viewport';

/*
 * Geometry along an element's own line (doc 98) — a fence, a wall, a hedge
 * drawn as one: pure, in garden metres with y north.
 */

export interface Station {
  at: Point;
  /** Which way the line runs there: radians, anticlockwise from east. */
  angle: number;
}

export function lengthOf(line: Point[]): number {
  let total = 0;
  for (let i = 1; i < line.length; i += 1) {
    total += Math.hypot(line[i]!.x - line[i - 1]!.x, line[i]!.y - line[i - 1]!.y);
  }
  return total;
}

/** Every `spacing` along the line from `start`, never past its end: where,
 *  and which way the line runs there. */
export function stations(line: Point[], spacing: number, start = 0): Station[] {
  const found: Station[] = [];
  if (spacing <= 0 || line.length < 2) return found;
  let next = start;
  let travelled = 0;
  for (let i = 1; i < line.length; i += 1) {
    const a = line[i - 1]!;
    const b = line[i]!;
    const run = Math.hypot(b.x - a.x, b.y - a.y);
    if (run === 0) continue;
    const angle = Math.atan2(b.y - a.y, b.x - a.x);
    for (; next <= travelled + run + 1e-9; next += spacing) {
      const t = (next - travelled) / run;
      found.push({ at: { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t }, angle });
    }
    travelled += run;
  }
  return found;
}

/** The left-hand normal of each segment. */
function normals(line: Point[]): Point[] {
  return line.slice(1).map((b, i) => {
    const a = line[i]!;
    const run = Math.hypot(b.x - a.x, b.y - a.y) || 1;
    return { x: -(b.y - a.y) / run, y: (b.x - a.x) / run };
  });
}

/** The line moved `offset` to its left (negative: its right), corners mitred. */
export function parallel(line: Point[], offset: number): Point[] {
  if (offset === 0 || line.length < 2) return line.map((p) => ({ ...p }));
  const sides = normals(line);
  return line.map((p, i) => {
    const before = sides[i - 1];
    const after = sides[i];
    const one = before ?? after!;
    if (before === undefined || after === undefined) {
      return { x: p.x + one.x * offset, y: p.y + one.y * offset };
    }
    const mitre = { x: before.x + after.x, y: before.y + after.y };
    const along = before.x * mitre.x + before.y * mitre.y;
    if (Math.abs(along) < 1e-9) return { x: p.x + before.x * offset, y: p.y + before.y * offset };
    return { x: p.x + (mitre.x * offset) / along, y: p.y + (mitre.y * offset) / along };
  });
}

interface Axis {
  ux: number;
  uy: number;
  along: [number, number];
  across: [number, number];
}

/** The outline measured along its longest edge and across it. */
function axis(points: Point[]): Axis {
  let longest = 0;
  let ux = 1;
  let uy = 0;
  points.forEach((a, i) => {
    const b = points[(i + 1) % points.length]!;
    const run = Math.hypot(b.x - a.x, b.y - a.y);
    if (run > longest) [longest, ux, uy] = [run, (b.x - a.x) / run, (b.y - a.y) / run];
  });
  const along = points.map((p) => p.x * ux + p.y * uy);
  const across = points.map((p) => -p.x * uy + p.y * ux);
  return {
    ux, uy,
    along: [Math.min(...along), Math.max(...along)],
    across: [Math.min(...across), Math.max(...across)],
  };
}

/** The long axis of a thin outline — a fence or a wall drawn as a rectangle —
 *  from end to end through its middle. */
export function centreline(points: Point[]): Point[] {
  if (points.length < 2) return points.map((p) => ({ ...p }));
  const { ux, uy, along, across } = axis(points);
  const middle = (across[0] + across[1]) / 2;
  return along.map((a) => ({ x: a * ux - middle * uy, y: a * uy + middle * ux }));
}

/** Half the outline's width across its long axis. */
export function halfWidth(points: Point[]): number {
  if (points.length < 2) return 0;
  const { across } = axis(points);
  return (across[1] - across[0]) / 2;
}
