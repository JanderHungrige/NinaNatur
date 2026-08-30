/**
 * Cleaning up after the hand.
 *
 * A freehand stroke is four hundred jittered points that mean a shape with six
 * corners, usually not quite closed and often crossing itself. Every function
 * here turns one of those facts into the shape the user meant, because the
 * alternative is a drawing tool that demands precision — which is a form with
 * extra steps.
 */
import { type Point, area, selfIntersects } from './geometry';

/** Perpendicular distance from `p` to the line through `a` and `b`. */
function distanceToLine(p: Point, a: Point, b: Point): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const length = Math.hypot(dx, dy);
  // A zero-length segment is a point, so the distance is to that point.
  if (length === 0) return Math.hypot(p.x - a.x, p.y - a.y);
  return Math.abs(dy * p.x - dx * p.y + b.x * a.y - b.y * a.x) / length;
}

/**
 * Ramer–Douglas–Peucker: drop every point the shape can be described without.
 *
 * `tolerance` is in metres, so it means the same thing at every zoom level —
 * a simplification measured in pixels would erase a shape's corners on a
 * zoomed-out view and keep the hand's tremor on a close one.
 */
export function simplify(points: Point[], tolerance: number): Point[] {
  if (points.length <= 2) return [...points];

  const first = points[0];
  const last = points[points.length - 1];
  if (first === undefined || last === undefined) return [...points];

  let worst = 0;
  let index = 0;
  for (let i = 1; i < points.length - 1; i += 1) {
    const candidate = points[i];
    if (candidate === undefined) continue;
    const distance = distanceToLine(candidate, first, last);
    if (distance > worst) {
      worst = distance;
      index = i;
    }
  }

  if (worst <= tolerance) return [first, last];

  // Recurse on both halves; the split point belongs to both and is de-duplicated.
  const left = simplify(points.slice(0, index + 1), tolerance);
  const right = simplify(points.slice(index), tolerance);
  return [...left.slice(0, -1), ...right];
}

/**
 * Close the outline when the hand came back near where it started.
 *
 * Closing means dropping the stray end, not appending the first point: a
 * polygon is closed by being a polygon, and a duplicated first corner is a
 * zero-length edge for everything downstream to trip over.
 */
export function closeIfNear(points: Point[], within: number): Point[] {
  // Three points that end near the start are still a triangle. Dropping one
  // would leave two, which is not a shape at all.
  if (points.length <= 3) return [...points];
  const first = points[0];
  const last = points[points.length - 1];
  if (first === undefined || last === undefined) return [...points];
  return Math.hypot(last.x - first.x, last.y - first.y) <= within
    ? points.slice(0, -1)
    : [...points];
}

/** The average of the corners. Not the centroid of the area, which a
 *  self-crossing outline does not have a meaningful one of. */
function meanPoint(points: Point[]): Point {
  const sum = points.reduce((acc, p) => ({ x: acc.x + p.x, y: acc.y + p.y }), { x: 0, y: 0 });
  return { x: sum.x / points.length, y: sum.y / points.length };
}

/** Andrew's monotone chain. The fallback, not the method — see below. */
function convexHull(points: Point[]): Point[] {
  const sorted = [...points].sort((a, b) => a.x - b.x || a.y - b.y);
  const cross = (o: Point, a: Point, b: Point): number =>
    (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);

  const build = (source: Point[]): Point[] => {
    const chain: Point[] = [];
    for (const point of source) {
      while (chain.length >= 2) {
        const a = chain[chain.length - 2];
        const b = chain[chain.length - 1];
        if (a === undefined || b === undefined || cross(a, b, point) > 0) break;
        chain.pop();
      }
      chain.push(point);
    }
    return chain.slice(0, -1);
  };

  return [...build(sorted), ...build([...sorted].reverse())];
}

/**
 * Untangle a stroke that crosses itself.
 *
 * A shape that does not cross itself is returned untouched — including a
 * concave one. That is the whole reason this is not simply a convex hull: an
 * L-shaped bed is an ordinary thing to draw, and a hull fills in its notch.
 *
 * When the stroke does cross, the corners are re-ordered by their angle around
 * the middle of the shape. That resolves the scribble people actually make —
 * a stroke that doubles back — into an outline through the same corners, and
 * it cannot fail to terminate. It can still leave a crossing in a genuinely
 * pathological stroke, and then the hull is taken: something drawn is better
 * than a refusal the user cannot act on.
 *
 * Returns null when there is nothing to save: fewer than three corners is a
 * line, and inventing the third would put a shape on the plan nobody drew.
 */
export function resolveOverlap(points: Point[]): Point[] | null {
  if (points.length < 3) return null;
  if (!selfIntersects(points)) return [...points];

  const middle = meanPoint(points);
  const sorted = [...points].sort(
    (a, b) =>
      Math.atan2(a.y - middle.y, a.x - middle.x) -
      Math.atan2(b.y - middle.y, b.x - middle.x),
  );
  if (!selfIntersects(sorted)) return sorted;

  const hull = convexHull(points);
  return hull.length >= 3 ? hull : null;
}

/** Below this a "shape" is a line the hand wobbled along. */
const MIN_AREA_M2 = 0.01;

/** Centimetres. A hand-drawn outline is not a survey, and full float precision
 *  stores seventeen digits of pointer noise per corner. */
const round = (value: number): number => Math.round(value * 100) / 100;

/**
 * The whole clean-up, in the order the steps depend on each other: thin the
 * stream first so the later steps work on corners rather than on tremor, close
 * it, then untangle what is left.
 */
export function tidy(
  stroke: Point[],
  options: { tolerance: number; closeWithin: number },
): Point[] | null {
  const thinned = simplify(stroke, options.tolerance);
  const closed = closeIfNear(thinned, options.closeWithin);
  const untangled = resolveOverlap(closed);
  if (untangled === null) return null;

  const rounded = untangled.map((p) => ({ x: round(p.x), y: round(p.y) }));
  // Checked after rounding, because rounding is what can flatten a sliver.
  if (rounded.length < 3 || Math.abs(area(rounded)) < MIN_AREA_M2) return null;
  return rounded;
}
