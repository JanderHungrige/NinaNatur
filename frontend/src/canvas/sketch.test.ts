import { describe, expect, it } from 'vitest';

import { offset, overshoots, ticks, wobble } from './sketch';

/* The geometry a sketched outline is drawn with (doc 97): pure, seeded, in metres. */

const square = [{ x: 0, y: 0 }, { x: 4, y: 0 }, { x: 4, y: 4 }, { x: 0, y: 4 }];

/** Distance from a point to the square's outline. */
function offOutline(p: { x: number; y: number }): number {
  if (p.x >= 0 && p.x <= 4 && p.y >= 0 && p.y <= 4) return Math.min(p.x, 4 - p.x, p.y, 4 - p.y);
  const dx = Math.max(0 - p.x, 0, p.x - 4);
  const dy = Math.max(0 - p.y, 0, p.y - 4);
  return Math.hypot(dx, dy);
}

describe('wobble — an ink line that wavers like a pen', () => {
  it('stays within its amplitude of the outline it follows', () => {
    const line = wobble(square, 0.1, 1, 1);
    expect(line.length).toBeGreaterThan(square.length * 3);
    for (const p of line) expect(offOutline(p)).toBeLessThanOrEqual(0.1 + 1e-9);
  });

  it('is the same line every time for the same seed, and another line for another', () => {
    expect(wobble(square, 0.1, 1, 7)).toEqual(wobble(square, 0.1, 1, 7));
    expect(wobble(square, 0.1, 1, 7)).not.toEqual(wobble(square, 0.1, 1, 8));
  });

  it('with no amplitude is the outline itself', () => {
    for (const p of wobble(square, 0, 1, 1)) expect(offOutline(p)).toBeLessThan(1e-9);
  });
});

describe('overshoots — the corners a hand draws past', () => {
  it('carries every edge on past both its ends', () => {
    const marks = overshoots(square, 0.3);
    expect(marks).toHaveLength(8);
    // The bottom edge, carried on past its left end and past its right end.
    expect(marks).toContainEqual([{ x: 0, y: 0 }, { x: -0.3, y: 0 }]);
    expect(marks).toContainEqual([{ x: 4, y: 0 }, { x: 4.3, y: 0 }]);
  });
});

describe('ticks — the marks along the inside of a building', () => {
  const inside = (p: { x: number; y: number }) => p.x > 0 && p.x < 4 && p.y > 0 && p.y < 4;

  it('are spaced along the whole outline, inside it, whichever way round it runs', () => {
    for (const outline of [square, [...square].reverse()]) {
      const marks = ticks(outline, 1, 0.2, 90, 0.1);
      expect(marks).toHaveLength(16);
      for (const [a, b] of marks) {
        const middle = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
        expect(inside(middle)).toBe(true);
        expect(offOutline(middle)).toBeCloseTo(0.1, 9);
        expect(Math.hypot(b.x - a.x, b.y - a.y)).toBeCloseTo(0.2, 9);
      }
    }
  });
});

describe('offset — a shadow where the drawing puts it', () => {
  it('moves every corner by the same amount', () => {
    expect(offset(square, 0.5, -0.5)).toEqual([
      { x: 0.5, y: -0.5 }, { x: 4.5, y: -0.5 }, { x: 4.5, y: 3.5 }, { x: 0.5, y: 3.5 },
    ]);
  });
});
