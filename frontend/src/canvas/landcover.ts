import type { GardenOut, Landcover } from '../api/client';

/**
 * The land around a garden as the plan draws it (doc 114): one path per class,
 * and the plot cut out of all of them. Pure, so it is tested without drawing.
 */

export type LandKind = Landcover['areas'][number]['kind'];

/** One class of land, as the one path that draws it. */
export interface LandPath {
  kind: LandKind;
  d: string;
}

/** A ring in garden metres (y north) as a closed SVG subpath (y down). */
export function ringPath(ring: number[][]): string {
  const moves = ring.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0] ?? 0} ${-(p[1] ?? 0)}`);
  return `${moves.join('')}Z`;
}

/** Positive for a ring that runs anticlockwise with y north (shoelace). */
export function signedArea(ring: number[][]): number {
  let twice = 0;
  ring.forEach((p, i) => {
    const q = ring[(i + 1) % ring.length] ?? p;
    twice += (p[0] ?? 0) * (q[1] ?? 0) - (q[0] ?? 0) * (p[1] ?? 0);
  });
  return twice / 2;
}

/**
 * One path per class, in drawing order: the class whose largest area is the
 * largest first, so it lies behind — a residential quarter under the park in
 * it, a wood under its pond. The server turns holes against their outline, so
 * the nonzero rule keeps holes open and two overlapping lawns one lawn.
 */
export function landPaths(landcover: Landcover): LandPath[] {
  const byKind = new Map<LandKind, { d: string[]; largest: number }>();
  for (const area of landcover.areas) {
    const entry = byKind.get(area.kind) ?? { d: [], largest: 0 };
    for (const ring of area.rings) {
      entry.d.push(ringPath(ring));
      entry.largest = Math.max(entry.largest, signedArea(ring));
    }
    byKind.set(area.kind, entry);
  }
  return [...byKind]
    .sort((a, b) => b[1].largest - a[1].largest)
    .map(([kind, entry]) => ({ kind, d: entry.d.join('') }));
}

/** The garden's own ground: what no class of land may tint. */
export function plotsOf(obstacles: GardenOut['obstacles']): number[][][] {
  return obstacles.filter((o) => o.kind === 'garden').map((o) => o.footprint);
}

/**
 * Everything but the plot, as one path for an even-odd clip: a rectangle round
 * the land and the plot, with the plot's outline inside it. Null without a
 * plot — a garden drawn by hand has none, and then nothing is cut out.
 */
export function outsidePlots(landcover: Landcover, plots: number[][][]): string | null {
  if (plots.length === 0) return null;
  // A loop, not Math.min(...points): a forest's edge can be more points than
  // a call takes arguments.
  let [left, bottom, right, top] = [Infinity, Infinity, -Infinity, -Infinity];
  for (const [x = 0, y = 0] of [...landcover.areas.flatMap((a) => a.rings.flat()), ...plots.flat()]) {
    [left, bottom, right, top] = [Math.min(left, x), Math.min(bottom, y), Math.max(right, x), Math.max(top, y)];
  }
  const frame = ringPath([[left - 1, bottom - 1], [right + 1, bottom - 1], [right + 1, top + 1],
    [left - 1, top + 1]]);
  return frame + plots.map(ringPath).join('');
}
