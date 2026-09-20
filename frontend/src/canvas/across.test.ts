import { describe, expect, it } from 'vitest';

import { acrossPairs, acrossPoints } from './across';

/* How wide a thing is, for the theme's level of detail (doc 99). */

describe('how wide a thing is', () => {
  it('is its longer side, whichever way round it lies', () => {
    expect(acrossPairs([[0, 0], [9, 0], [9, 6], [0, 6]])).toBe(9);
    expect(acrossPairs([[0, 0], [6, 0], [6, 9], [0, 9]])).toBe(9);
    // Wherever it stands: a width is not a distance from the origin.
    expect(acrossPairs([[100, 50], [109, 50], [109, 56], [100, 56]])).toBe(9);
  });

  it('reads points as well as pairs, so a shape and its marks agree', () => {
    const box = [{ x: -2, y: -1.5 }, { x: 2, y: -1.5 }, { x: 2, y: 1.5 }, { x: -2, y: 1.5 }];
    expect(acrossPoints(box)).toBe(4);
  });

  it('and answers nothing for nothing, rather than -Infinity', () => {
    expect(acrossPairs([])).toBe(0);
    expect(acrossPoints([])).toBe(0);
  });
});
