/**
 * Editing an outline corner by corner.
 *
 * The behaviour every flowchart tool has, and the reason a drawn bed can follow
 * a boundary that is not a rectangle. All of it works on the points an element
 * already stores, so nothing converts: Wave 11 keeps points precisely so that
 * dragging one has nothing to undo.
 */

export type Vertices = number[][];

/** Three corners are the fewest that enclose anything. */
export const MIN_VERTICES = 3;

/** Centimetres, like every other stored coordinate. */
const round = (v: number): number => Math.round(v * 100) / 100;

/**
 * Where a corner could be inserted: the middle of each edge.
 *
 * `closed` decides whether the edge from the last point back to the first
 * counts. It does for an area and does not for a line — offering it on a path
 * would put a handle in mid-air between two ends that are not joined.
 */
export function midpoints(
  points: Vertices,
  options: { closed?: boolean } = {},
): Array<{ index: number; at: [number, number] }> {
  const closed = options.closed !== false;
  const last = closed ? points.length : points.length - 1;
  const found: Array<{ index: number; at: [number, number] }> = [];
  for (let i = 0; i < last; i += 1) {
    const a = points[i];
    const b = points[(i + 1) % points.length];
    if (a === undefined || b === undefined) continue;
    found.push({
      index: i,
      at: [round((a[0]! + b[0]!) / 2), round((a[1]! + b[1]!) / 2)],
    });
  }
  return found;
}

/** Add a corner in the middle of edge `index`. */
export function insertVertex(points: Vertices, index: number): Vertices {
  const mid = midpoints(points).find((m) => m.index === index);
  if (mid === undefined) return [...points];
  const grown = [...points];
  grown.splice(index + 1, 0, [mid.at[0], mid.at[1]]);
  return grown;
}

export function moveVertex(points: Vertices, index: number, to: number[]): Vertices {
  return points.map((p, i) => (i === index ? [round(to[0]!), round(to[1]!)] : p));
}

/** Remove a corner, or refuse when what is left would not be a shape. */
export function removeVertex(points: Vertices, index: number): Vertices | null {
  if (points.length <= MIN_VERTICES) return null;
  return points.filter((_, i) => i !== index);
}
