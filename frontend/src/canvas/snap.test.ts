import { describe, expect, it } from 'vitest';

import { snap, snapPoint } from './snap';

describe('snapping', () => {
  it('rounds to the nearest grid line', () => {
    expect(snap(3.4, 1)).toBe(3);
    expect(snap(3.6, 1)).toBe(4);
  });

  it('snaps to whatever the grid currently is, not always to metres', () => {
    // At 200 m across the grid is 25 m. Snapping to 1 m there would put points
    // between visible lines, which reads as a broken snap rather than a fine one.
    expect(snap(37, 25)).toBe(25);
    expect(snap(38, 25)).toBe(50);
  });

  it('handles negative coordinates symmetrically', () => {
    // West and south of the origin are ordinary places to draw.
    expect(snap(-3.4, 1)).toBe(-3);
    expect(snap(-3.6, 1)).toBe(-4);
  });

  it('leaves a point alone when the user asks for free placement', () => {
    // Alt held: a hedge does not run along grid lines just because we drew one.
    const free = snapPoint({ x: 3.42, y: -7.19 }, 1, { free: true });
    expect(free).toEqual({ x: 3.42, y: -7.19 });
  });

  it('snaps both axes when it snaps', () => {
    expect(snapPoint({ x: 3.42, y: -7.19 }, 1, { free: false })).toEqual({ x: 3, y: -7 });
  });

  it('never returns -0', () => {
    // -0 survives JSON, prints as "-0", and makes two identical polygons compare
    // unequal in a test.
    expect(Object.is(snap(-0.2, 1), 0)).toBe(true);
  });
});
