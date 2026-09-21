import { describe, expect, it } from 'vitest';

import { inset, offset, overshoots, scaled, sweep, ticks, wobble, wobbleLine } from './sketch';

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

describe('the marks doc 98 adds', () => {
  it('insets an outline by the same distance on every side, whichever way it runs', () => {
    const inner = [{ x: 0.5, y: 0.5 }, { x: 3.5, y: 0.5 }, { x: 3.5, y: 3.5 }, { x: 0.5, y: 3.5 }];
    expect(inset(square, 0.5)).toEqual(inner);
    expect(inset([...square].reverse(), 0.5)).toEqual([...inner].reverse());
  });

  it('draws a ring smaller about its middle', () => {
    expect(scaled(square, 0.5)).toEqual([
      { x: 1, y: 1 }, { x: 3, y: 1 }, { x: 3, y: 3 }, { x: 1, y: 3 },
    ]);
  });

  it('hatches only the side in shade, and swells and shrinks where told', () => {
    // His light comes from the upper left: the shade is to the south-east.
    const shade = ticks(square, 1, 0.2, 90, 0.1, { facing: { x: 1, y: -1 } });
    expect(shade).toHaveLength(8);
    for (const [a, b] of shade) expect(Math.min(a.x, b.x) > 3 || Math.min(a.y, b.y) < 1).toBe(true);
    const varied = ticks(square, 1, 0.2, 90, 0, { sizes: [0.5, 1.5] });
    const lengths = varied.map(([a, b]) => Math.hypot(b.x - a.x, b.y - a.y));
    expect(lengths[0]).toBeCloseTo(0.1, 9);
    expect(lengths[1]).toBeCloseTo(0.3, 9);
  });

  it('wavers along an open line from its first point to its last', () => {
    const line = [{ x: 0, y: 0 }, { x: 10, y: 0 }];
    const drawn = wobbleLine(line, 0.1, 1, 3);
    expect(drawn.length).toBeGreaterThan(10);
    for (const p of drawn) expect(Math.abs(p.y)).toBeLessThanOrEqual(0.1 + 1e-9);
    expect(drawn[drawn.length - 1]!.x).toBeCloseTo(10, 9);
  });
});

describe('a shape swept along the light (doc 99)', () => {
  const box = [{ x: 0, y: 0 }, { x: 2, y: 0 }, { x: 2, y: 1 }, { x: 0, y: 1 }];

  it('covers the shape, its offset copy and the ground between them', () => {
    const cast = sweep(box, 3, 1);
    // The hull of both boxes: nothing of either sticks out of it.
    for (const p of [...box, ...box.map((q) => ({ x: q.x + 3, y: q.y + 1 }))]) {
      expect(inside(cast, p)).toBe(true);
    }
    // And it reaches the far corner of the offset copy, not merely the shape.
    expect(Math.max(...cast.map((p) => p.x))).toBeCloseTo(5, 6);
    expect(Math.max(...cast.map((p) => p.y))).toBeCloseTo(2, 6);
  });

  it('is the shape itself where the light casts nothing', () => {
    expect(sweep(box, 0, 0).length).toBeLessThanOrEqual(box.length);
    expect(Math.max(...sweep(box, 0, 0).map((p) => p.x))).toBeCloseTo(2, 6);
  });

  it('keeps the hull convex: no inner corner survives a sweep', () => {
    // An L, swept: the notch is filled in, as a shadow's edge has no notch.
    const ell = [{ x: 0, y: 0 }, { x: 3, y: 0 }, { x: 3, y: 1 },
                 { x: 1, y: 1 }, { x: 1, y: 3 }, { x: 0, y: 3 }];
    const cast = sweep(ell, 1, 1);
    expect(inside(cast, { x: 2.5, y: 2.5 })).toBe(true);
  });
});

/** Is the point inside this convex ring? Winding all one way says so. */
function inside(ring: { x: number; y: number }[], p: { x: number; y: number }): boolean {
  let sign = 0;
  for (let i = 0; i < ring.length; i += 1) {
    const a = ring[i]!;
    const b = ring[(i + 1) % ring.length]!;
    const cross = (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x);
    if (Math.abs(cross) < 1e-9) continue;
    const at = cross > 0 ? 1 : -1;
    if (sign !== 0 && at !== sign) return false;
    sign = at;
  }
  return true;
}
