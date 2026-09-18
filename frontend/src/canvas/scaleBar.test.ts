import { describe, expect, it } from 'vitest';

import { scaleBar } from './scaleBar';

/* The plan's scale bar (doc 98): true at every zoom, in lengths a person reads. */

describe('scaleBar', () => {
  it('is the shortest 1-2-5 length at least so many pixels long, and exactly that long', () => {
    expect(scaleBar(0.111, 48)).toEqual({ metres: 10, pixels: 10 / 0.111 });
    expect(scaleBar(0.0333, 48)).toEqual({ metres: 2, pixels: 2 / 0.0333 });
    expect(scaleBar(0.333, 48)).toEqual({ metres: 20, pixels: 20 / 0.333 });
    expect(scaleBar(1.2, 48).metres).toBe(100);
  });

  it('never claims a length it does not draw', () => {
    for (const mpp of [0.004, 0.02, 0.07, 0.4, 2.5, 9]) {
      const bar = scaleBar(mpp, 48);
      expect(bar.pixels * mpp).toBeCloseTo(bar.metres, 9);
      expect(bar.pixels).toBeGreaterThanOrEqual(48);
      expect(bar.pixels).toBeLessThan(48 * 2.5 + 1e-9);
    }
  });
});
