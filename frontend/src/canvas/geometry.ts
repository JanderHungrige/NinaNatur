/**
 * Whether a drawn shape is one that can be stored.
 *
 * The checks here exist because the rest of the system assumes a polygon has an
 * inside: the shading model samples its centroid, the room check divides by its
 * area. A degenerate shape does not fail loudly there — it produces a confident
 * number from nothing.
 */
import type { Point } from './viewport';

export type { Point };

/** Below this two points are the same click as far as a person is concerned. */
const EPSILON_M = 1e-6;

/** Twice the signed area — positive or negative depending on winding. */
function shoelace(points: Point[]): number {
  let total = 0;
  for (let i = 0; i < points.length; i += 1) {
    const a = points[i] as Point;
    const b = points[(i + 1) % points.length] as Point;
    total += a.x * b.y - b.x * a.y;
  }
  return total;
}

/** Area in square metres, independent of which way the polygon was drawn. */
export function area(points: Point[]): number {
  if (points.length < 3) return 0;
  return Math.abs(shoelace(points)) / 2;
}

/**
 * Whether this is a shape with no inside.
 *
 * Two clicks and a double-click is a line, not a bed; three clicks along a
 * fence is still a line. Saved anyway, they reach the area and shading code as
 * shapes that have a centroid and no extent.
 */
export function isDegenerate(points: Point[]): boolean {
  if (points.length < 3) return true;
  return area(points) <= EPSILON_M;
}

function onSegment(a: Point, b: Point, p: Point): boolean {
  return (
    Math.min(a.x, b.x) - EPSILON_M <= p.x &&
    p.x <= Math.max(a.x, b.x) + EPSILON_M &&
    Math.min(a.y, b.y) - EPSILON_M <= p.y &&
    p.y <= Math.max(a.y, b.y) + EPSILON_M
  );
}

function cross(o: Point, a: Point, b: Point): number {
  return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
}

function segmentsCross(a1: Point, a2: Point, b1: Point, b2: Point): boolean {
  const d1 = cross(a1, a2, b1);
  const d2 = cross(a1, a2, b2);
  const d3 = cross(b1, b2, a1);
  const d4 = cross(b1, b2, a2);
  if (((d1 > 0) !== (d2 > 0)) && ((d3 > 0) !== (d4 > 0))) return true;
  // Collinear overlap.
  if (Math.abs(d1) <= EPSILON_M && onSegment(a1, a2, b1)) return true;
  if (Math.abs(d2) <= EPSILON_M && onSegment(a1, a2, b2)) return true;
  if (Math.abs(d3) <= EPSILON_M && onSegment(b1, b2, a1)) return true;
  return Math.abs(d4) <= EPSILON_M && onSegment(b1, b2, a2);
}

/**
 * Whether the outline crosses itself — a bow tie, easy to draw by accident.
 *
 * Neighbouring edges always meet at their shared vertex, and the closing edge
 * meets the first one, so those pairs are skipped: treating a shared corner as
 * a crossing would reject every polygon ever drawn.
 */
export function selfIntersects(points: Point[]): boolean {
  const n = points.length;
  if (n < 4) return false;
  for (let i = 0; i < n; i += 1) {
    for (let j = i + 1; j < n; j += 1) {
      const adjacent = j === i + 1 || (i === 0 && j === n - 1);
      if (adjacent) continue;
      if (
        segmentsCross(
          points[i] as Point,
          points[(i + 1) % n] as Point,
          points[j] as Point,
          points[(j + 1) % n] as Point,
        )
      ) {
        return true;
      }
    }
  }
  return false;
}

/**
 * Whether a point lies inside an outline.
 *
 * Ray casting, the same rule the server's `covers` uses — a bed's notch is not
 * in the bed, and anything placing things inside a shape has to know that.
 * Points exactly on an edge are not worth deciding: nothing here places a
 * flower to the millimetre.
 */
export function covers(polygon: Point[], at: Point): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i, i += 1) {
    const a = polygon[i]!;
    const b = polygon[j]!;
    const straddles = a.y > at.y !== b.y > at.y;
    if (!straddles) continue;
    const crossing = a.x + ((at.y - a.y) / (b.y - a.y)) * (b.x - a.x);
    if (at.x < crossing) inside = !inside;
  }
  return inside;
}
