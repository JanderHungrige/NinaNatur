/**
 * Snapping, done in garden metres.
 *
 * After the transform, never before it: snapping screen pixels and converting
 * afterwards gives a different answer at every zoom level, so the coordinate
 * that ends up stored would depend on how far the user had zoomed in when they
 * drew it.
 */
import type { Point } from './viewport';

/** Round to the nearest multiple of `spacing`. */
export function snap(value: number, spacing: number): number {
  if (spacing <= 0) return value;
  const snapped = Math.round(value / spacing) * spacing;
  // `-0` survives JSON, prints as "-0", and makes two identical polygons compare
  // unequal in a test for no reason a reader would ever guess.
  return snapped === 0 ? 0 : snapped;
}

export function snapPoint(
  point: Point,
  spacing: number,
  options: { free: boolean },
): Point {
  // Free placement is held, not toggled: a hedge does not run along grid lines
  // just because the tool drew some.
  if (options.free) return point;
  return { x: snap(point.x, spacing), y: snap(point.y, spacing) };
}
