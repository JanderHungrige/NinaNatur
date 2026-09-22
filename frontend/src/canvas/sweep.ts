/*
 * NinaNatur. A shape swept along a light, as the ground it hides all the way
 * over (docs 99, 116): the drop shadow of Draft Sketch's standing things, built
 * from the same pieces as `ninanatur/solar/sweep.py` builds the day's shadows.
 */
import { selfIntersects } from './geometry';
import { offset } from './sketch';
import type { Point } from './viewport';

/** Below this a piece is a wall swept along its own length: no ground. */
const FLAT_M2 = 1e-9;

/**
 * The shape swept along a light, as pieces whose union is the ground it hides
 * all the way over (docs 99, 116).
 *
 * A cast shadow is not the shape moved — that leaves a gap between a house and
 * its own shadow, which reads as a second building. For a convex outline it is
 * the hull of the outline and its offset copy: one piece, the same points as
 * ever. For a concave one the hull fills an L's open corner, which the light
 * model counts as sun, so the pieces are kept — the outline, its copy and the
 * band each wall sweeps — all turned the same way, so a path of all of them
 * fills their union under the non-zero rule. `ninanatur/solar/sweep.py` builds
 * the same pieces.
 */
export function sweep(points: Point[], dx: number, dy: number): Point[][] {
  const ring = cleaned(points);
  const moved = offset(ring, dx, dy);
  // An outline that crosses itself has lobes wound opposite ways, and one of
  // them would cancel a band under the non-zero rule: it keeps the hull, as
  // every shadow did before (review, 2026-09-22).
  if (ring.length < 3 || isConvex(ring) || selfIntersects(ring)) {
    return [hull([...ring, ...moved])];
  }
  const bands = ring.map((a, i) => {
    const b = ring[(i + 1) % ring.length]!;
    return [a, b, { x: b.x + dx, y: b.y + dy }, { x: a.x + dx, y: a.y + dy }];
  });
  return [ring, moved, ...bands]
    .filter((piece) => Math.abs(signedArea(piece)) > FLAT_M2)
    .map((piece) => (signedArea(piece) > 0 ? piece : [...piece].reverse()));
}

function same(a: Point, b: Point): boolean {
  return a.x === b.x && a.y === b.y;
}

/**
 * The outline without a point repeated back to back, without the closing
 * point OpenStreetMap repeats, and without spurs: a wall drawn as a line has
 * one at the inside of every corner, where its band runs past the corner and
 * straight back. Its tip is not a corner of the wall, and read as one it made
 * every turning wall convex (review, 2026-09-22).
 */
function cleaned(points: Point[]): Point[] {
  const ring = points.filter((p, i) => i === 0 || !same(p, points[i - 1]!));
  if (ring.length > 1 && same(ring[0]!, ring[ring.length - 1]!)) ring.pop();
  let spur = spurAt(ring);
  while (spur >= 0 && ring.length > 3) {
    ring.splice(spur, 1);
    spur = spurAt(ring);
  }
  return ring;
}

/** The corner where the outline doubles straight back, or -1. */
function spurAt(ring: Point[]): number {
  const n = ring.length;
  for (let i = 0; i < n; i += 1) {
    const a = ring[(i + n - 1) % n]!;
    const b = ring[i]!;
    const c = ring[(i + 1) % n]!;
    const back = (b.x - a.x) * (c.x - b.x) + (b.y - a.y) * (c.y - b.y) < 0;
    if (back && Math.abs(turn(a, b, c)) <= FLAT_M2) return i;
  }
  return -1;
}

function turn(o: Point, a: Point, b: Point): number {
  return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
}

function signedArea(ring: Point[]): number {
  let twice = 0;
  ring.forEach((a, i) => {
    const b = ring[(i + 1) % ring.length]!;
    twice += a.x * b.y - b.x * a.y;
  });
  return twice / 2;
}

/** Every corner turns the same way; a straight run is not a turn. */
function isConvex(ring: Point[]): boolean {
  const turns = new Set<boolean>();
  ring.forEach((a, i) => {
    const cross = turn(a, ring[(i + 1) % ring.length]!, ring[(i + 2) % ring.length]!);
    if (Math.abs(cross) > FLAT_M2) turns.add(cross > 0);
  });
  return turns.size <= 1;
}

/** Andrew's monotone chain, as `ninanatur/solar/sweep.py` does it. */
function hull(all: Point[]): Point[] {
  const order = [...all].sort((a, b) => (a.x === b.x ? a.y - b.y : a.x - b.x));
  const half = (from: Point[]): Point[] => {
    const chain: Point[] = [];
    for (const p of from) {
      while (chain.length >= 2 && turn(chain[chain.length - 2]!, chain[chain.length - 1]!, p) <= 0) {
        chain.pop();
      }
      chain.push(p);
    }
    chain.pop();
    return chain;
  };
  return [...half(order), ...half([...order].reverse())];
}
