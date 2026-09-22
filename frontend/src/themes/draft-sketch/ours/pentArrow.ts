/**
 * Provenance: NinaNatur, in the style of Draft Sketch
 *
 * Where a pent roof's arrow goes (doc 98): from its upper edge, down the
 * surveyed fall, inside the house. Its own module since the review of
 * 2026-09-22 found every quick answer wrong somewhere: aimed at the outline's
 * middle it leaned with the house; sized by that middle it ran off an L; started
 * at the bare middle of the edge it began over a notch; measured to the first
 * crossing it shrank to a dot where the drawn wall sat a millimetre outside the
 * outline, and in a recess it measured the recess.
 */
import { centreOf } from '../../../canvas/sketch';
import type { Point } from '../../../canvas/viewport';

/** How far a step is taken into the house before anything is believed: past
 *  the 5 cm the server straightens a wall by (`roof_lines.MIN_PIECE_M`) and the
 *  millimetres its lines are rounded to. */
const STEP_M = 0.05;
/** Where along each drawn wall a start is tried, middle first. */
const TRIES = [0.5, 0.35, 0.65, 0.2, 0.8, 0.05, 0.95];

/** The arrow's tail and tip, or null where no start on the drawn walls leads
 *  into the house. `bearing` is the surveyed fall; without one, the arrow aims
 *  at the outline's middle, as it always did. */
export function pentArrow(lines: [Point, Point][], ring: Point[],
  bearing: number | null | undefined): [Point, Point] | null {
  if (lines.length === 0 || ring.length < 3) return null;
  const [a, b] = upperEdge(lines);
  const middle = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  const down = bearing === null || bearing === undefined
    ? towards(nearestOn(lines, middle), centreOf(ring))
    : { x: Math.sin((bearing * Math.PI) / 180), y: Math.cos((bearing * Math.PI) / 180) };
  if (down === null) return null;
  const starts = [nearestOn(lines, middle),
    ...lines.flatMap(([p, q]) => TRIES.map((t) => ({ x: p.x + (q.x - p.x) * t, y: p.y + (q.y - p.y) * t })))];
  const arrows = starts.flatMap((from) => {
    if (!inside({ x: from.x + down.x * STEP_M, y: from.y + down.y * STEP_M }, ring)) return [];
    const run = leaving(from, down, ring);
    if (run === null) return [];
    const at = (share: number): Point => ({ x: from.x + down.x * run * share, y: from.y + down.y * run * share });
    const shaft: [Point, Point] = [at(0.125), at(0.55)];
    return [{ shaft, run, apart: Math.hypot(from.x - middle.x, from.y - middle.y),
              clear: clearance(shaft, ring) >= BARB_SPREAD * run }];
  });
  if (arrows.length === 0) return null;
  // Long enough to read, clear of the walls so its barbs are not cut, and then
  // as near the middle of the edge as that allows. Nearness alone started it
  // in the corner of a courtyard, running down the courtyard's wall or out of
  // the house within centimetres (review, 2026-09-22).
  const longest = Math.max(...arrows.map((a) => a.run));
  const long = arrows.filter((a) => a.run >= longest / 2);
  const pool = long.some((a) => a.clear) ? long.filter((a) => a.clear) : long;
  return pool.reduce((best, a) => (a.apart < best.apart ? a : best)).shaft;
}

/** How far a barb reaches sideways, as a share of the run: 30 % of the shaft
 *  (0.425 of the run) at 0.45 rad. */
const BARB_SPREAD = 0.3 * 0.425 * Math.sin(0.45);

/** How far the shaft keeps from the outline at its tail, middle and tip. */
function clearance([tail, tip]: [Point, Point], ring: Point[]): number {
  const mid = { x: (tail.x + tip.x) / 2, y: (tail.y + tip.y) / 2 };
  return Math.min(...[tail, mid, tip].map((p) => Math.min(...ring.map((a, i) => {
    const b = ring[(i + 1) % ring.length]!;
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const length = dx * dx + dy * dy;
    const t = length === 0 ? 0 : Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / length));
    return Math.hypot(a.x + t * dx - p.x, a.y + t * dy - p.y);
  }))));
}

function towards(from: Point, to: Point): Point | null {
  const length = Math.hypot(to.x - from.x, to.y - from.y);
  return length === 0 ? null : { x: (to.x - from.x) / length, y: (to.y - from.y) / length };
}

/** How far the ray runs before it leaves the outline: the first edge it crosses
 *  outwards, past the first step. An edge it crosses inwards — a wall the drawn
 *  line sits a hair outside of — is not where the house ends. */
function leaving(from: Point, way: Point, ring: Point[]): number | null {
  const turn = Math.sign(ring.reduce((sum, p, i) => {
    const q = ring[(i + 1) % ring.length]!;
    return sum + p.x * q.y - q.x * p.y;
  }, 0)) || 1;
  let nearest: number | null = null;
  ring.forEach((a, i) => {
    const b = ring[(i + 1) % ring.length]!;
    const ex = b.x - a.x;
    const ey = b.y - a.y;
    if (turn * (ey * way.x - ex * way.y) <= 0) return; // parallel, or crossed inwards
    const denominator = way.x * ey - way.y * ex;
    const t = ((a.x - from.x) * ey - (a.y - from.y) * ex) / denominator;
    const u = ((a.x - from.x) * way.y - (a.y - from.y) * way.x) / denominator;
    if (t > STEP_M && u >= 0 && u <= 1 && (nearest === null || t < nearest)) nearest = t;
  });
  return nearest;
}

/** Even-odd containment. */
export function inside(p: Point, ring: Point[]): boolean {
  let odd = false;
  ring.forEach((a, i) => {
    const b = ring[(i + 1) % ring.length]!;
    if ((a.y > p.y) !== (b.y > p.y) && p.x < a.x + ((p.y - a.y) * (b.x - a.x)) / (b.y - a.y)) odd = !odd;
  });
  return odd;
}

/** A pent's whole upper edge, end to end: the two ends farthest apart. */
function upperEdge(lines: [Point, Point][]): [Point, Point] {
  const ends = lines.flat();
  let best: [Point, Point] = lines[0]!;
  for (const p of ends) {
    for (const q of ends) {
      if (Math.hypot(q.x - p.x, q.y - p.y) > Math.hypot(best[1].x - best[0].x, best[1].y - best[0].y)) {
        best = [p, q];
      }
    }
  }
  return best;
}

/** The point on the drawn lines nearest to `p`. */
function nearestOn(lines: [Point, Point][], p: Point): Point {
  let best = lines[0]![0];
  let distance = Infinity;
  for (const [a, b] of lines) {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const length = dx * dx + dy * dy;
    const t = length === 0 ? 0 : Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / length));
    const q = { x: a.x + t * dx, y: a.y + t * dy };
    const d = Math.hypot(q.x - p.x, q.y - p.y);
    if (d < distance) {
      best = q;
      distance = d;
    }
  }
  return best;
}
