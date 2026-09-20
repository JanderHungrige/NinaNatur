/**
 * How wide a thing is on the ground, in metres: the longer side of the box
 * around it.
 *
 * It exists because a theme decides how much detail a shape can carry from how
 * big that shape is drawn (doc 99), and the two places that ask — the shapes
 * themselves and their decorations — hold their outlines in different shapes:
 * a footprint or a bed's polygon as `[x, y]` pairs, a decorated shape as
 * points. One measurement, so the fill and the marks over it cannot end up at
 * different levels of detail.
 */
import type { Point } from './viewport';

const spread = (values: readonly number[]): number =>
  values.length === 0 ? 0 : Math.max(...values) - Math.min(...values);

const longerSide = (xs: readonly number[], ys: readonly number[]): number =>
  Math.max(spread(xs), spread(ys));

/** From `[x, y]` pairs — a footprint, a bed's polygon, as the API sends them. */
export const acrossPairs = (pairs: readonly (readonly number[])[]): number =>
  longerSide(pairs.map((p) => p[0] ?? 0), pairs.map((p) => p[1] ?? 0));

/** From the points a shape is drawn from. */
export const acrossPoints = (points: readonly Point[]): number =>
  longerSide(points.map((p) => p.x), points.map((p) => p.y));
