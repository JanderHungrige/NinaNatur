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

/** Centimetres: a corner set freely is still not a survey mark. */
const toCentimetre = (v: number): number => Math.round(v * 100) / 100;

/**
 * The grid intersection when the point is within `within` metres of one, and
 * otherwise the point itself, to the centimetre.
 *
 * Magnetic rather than always (the owner's check, 2026-09-21): rounding every
 * click to a grid of at least a metre put corners up to half a metre from where
 * they were clicked, which read as the tool missing. The grid is faint, so it
 * pulls only from a few pixels away — the caller turns pixels into metres.
 */
export function snapNear(point: Point, spacing: number, within: number): Point {
  const grid = { x: snap(point.x, spacing), y: snap(point.y, spacing) };
  if (Math.hypot(grid.x - point.x, grid.y - point.y) <= within) return grid;
  return { x: toCentimetre(point.x) || 0, y: toCentimetre(point.y) || 0 };
}
