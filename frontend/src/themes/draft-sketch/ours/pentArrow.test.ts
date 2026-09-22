import { describe, expect, it } from 'vitest';

import type { Point } from '../../../canvas/viewport';
import { inside, pentArrow } from './pentArrow';

/* Where a pent roof's arrow goes (doc 98), with the lines the server's
   `roof_lines` really sends for each house (review, 2026-09-22). */

const pts = (...xy: [number, number][]): Point[] => xy.map(([x, y]) => ({ x, y }));
const line = (a: [number, number], b: [number, number]): [Point, Point] => [{ x: a[0], y: a[1] }, { x: b[0], y: b[1] }];
const length = ([a, b]: [Point, Point]) => Math.hypot(b.x - a.x, b.y - a.y);

describe('pentArrow', () => {
  it('runs a rectangle down its fall, from an eighth to a little past half its depth', () => {
    const house = pts([0, 0], [10, 0], [10, 8], [0, 8]);
    const [tail, tip] = pentArrow([line([10, 8], [0, 8])], house, 180)!;
    expect(tail.x).toBeCloseTo(5);
    expect(tail.y).toBeCloseTo(7);
    expect(tip.y).toBeCloseTo(8 - 0.55 * 8);
  });

  it('is not a dot where the drawn wall sits a hair outside the outline', () => {
    // An OpenStreetMap house whose uphill wall had a node on it; the server
    // drew the straightened wall, a millimetre or two off the outline.
    const house = pts([41.11, 5.82], [35.64, 11.47], [30.52, 6.51], [32.98, 3.98], [36.0, 0.87]);
    const shaft = pentArrow([line([30.52, 6.51], [36.0, 0.87])], house, 53.5)!;
    expect(length(shaft)).toBeGreaterThan(1);
    expect(inside(shaft[0], house) && inside(shaft[1], house)).toBe(true);
  });

  it('does not start in a recess and measure the recess', () => {
    const house = pts([0, 0], [10, 0], [10, 8], [6, 8], [6, 7], [4, 7], [4, 8], [0, 8]);
    const lines = [line([10, 8], [6, 8]), line([6, 7], [4, 7]), line([4, 8], [0, 8])];
    const shaft = pentArrow(lines, house, 182)!;
    expect(inside(shaft[0], house) && inside(shaft[1], house)).toBe(true);
    expect(length(shaft)).toBeGreaterThan(2);
  });

  it('keeps an L\'s arrow inside, whichever wall it starts from', () => {
    const house = pts([7.37, -9.81], [17.37, -9.81], [17.37, -4.81], [12.37, -4.81],
      [12.37, 0.19], [7.37, 0.19]);
    const lines = [line([17.37, -4.81], [12.37, -4.81]), line([12.37, 0.19], [7.37, 0.19])];
    const shaft = pentArrow(lines, house, 182)!;
    expect(inside(shaft[0], house) && inside(shaft[1], house)).toBe(true);
  });

  it('draws nothing rather than something over the garden', () => {
    // Lines that lead nowhere into the house: no arrow at all.
    expect(pentArrow([line([20, 20], [30, 20])], pts([0, 0], [10, 0], [10, 8], [0, 8]), 180))
      .toBeNull();
  });
});
