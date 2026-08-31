import { describe, expect, it } from 'vitest';

import { MAX_DOTS, bloomDots } from './blooms';

const SQUARE = [[0, 0], [10, 0], [10, 8], [0, 8]];

describe('bloomDots', () => {
  it('puts flowers inside the bed', () => {
    const dots = bloomDots(1, SQUARE, ['yellow', 'blue']);
    expect(dots.length).toBeGreaterThan(0);
    for (const dot of dots) {
      expect(dot.x).toBeGreaterThanOrEqual(0);
      expect(dot.x).toBeLessThanOrEqual(10);
      expect(dot.y).toBeGreaterThanOrEqual(0);
      expect(dot.y).toBeLessThanOrEqual(8);
    }
  });

  it('groups one colour together rather than scattering it', () => {
    // Nobody plants one salvia here and one over there. A colour's dots should
    // sit closer to each other than to the bed as a whole.
    const dots = bloomDots(1, SQUARE, ['yellow', 'blue']);
    const yellow = dots.filter((d) => d.colour === 'yellow');
    expect(yellow.length).toBeGreaterThan(2);

    const centre = {
      x: yellow.reduce((a, d) => a + d.x, 0) / yellow.length,
      y: yellow.reduce((a, d) => a + d.y, 0) / yellow.length,
    };
    const spread = Math.max(...yellow.map((d) => Math.hypot(d.x - centre.x, d.y - centre.y)));
    // Well inside the bed's own half-diagonal (~6.4 m).
    expect(spread).toBeLessThan(4);
  });

  it('keeps the clusters apart', () => {
    const dots = bloomDots(1, SQUARE, ['yellow', 'blue']);
    const mid = (c: string) => {
      const own = dots.filter((d) => d.colour === c);
      return {
        x: own.reduce((a, d) => a + d.x, 0) / own.length,
        y: own.reduce((a, d) => a + d.y, 0) / own.length,
      };
    };
    const a = mid('yellow');
    const b = mid('blue');
    expect(Math.hypot(a.x - b.x, a.y - b.y)).toBeGreaterThan(1.5);
  });

  it('draws the same bed the same way every time', () => {
    // Seeded from the bed's id. Without that the planting reshuffles on every
    // React render, which reads as the garden twitching.
    const once = bloomDots(7, SQUARE, ['yellow', 'blue']);
    const again = bloomDots(7, SQUARE, ['yellow', 'blue']);
    expect(again).toEqual(once);
  });

  it('draws two beds differently', () => {
    const a = bloomDots(1, SQUARE, ['yellow']);
    const b = bloomDots(2, SQUARE, ['yellow']);
    expect(b).not.toEqual(a);
  });

  it('stops adding dots past the point they mean anything', () => {
    const many = bloomDots(1, SQUARE, ['yellow', 'blue', 'white', 'pink', 'red', 'violet']);
    expect(many.length).toBeLessThanOrEqual(MAX_DOTS);
  });

  it('gives a small bed fewer flowers than a large one', () => {
    const small = bloomDots(1, [[0, 0], [2, 0], [2, 2], [0, 2]], ['yellow']);
    const large = bloomDots(1, [[0, 0], [30, 0], [30, 24], [0, 24]], ['yellow']);
    expect(small.length).toBeLessThan(large.length);
  });

  it('has nothing to draw without a colour', () => {
    expect(bloomDots(1, SQUARE, [])).toEqual([]);
  });

  it('keeps out of a notch in an L-shaped bed', () => {
    // The footprint is the bed, not its bounding box.
    const ell = [[0, 0], [10, 0], [10, 4], [4, 4], [4, 10], [0, 10]];
    const dots = bloomDots(3, ell, ['yellow', 'blue']);
    for (const dot of dots) {
      const inNotch = dot.x > 4.2 && dot.y > 4.2;
      expect(inNotch).toBe(false);
    }
  });
});
