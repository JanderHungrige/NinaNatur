import { describe, expect, it } from 'vitest';

import { closeIfNear, resolveOverlap, simplify, tidy, traceFrom } from './freehand';

/** A jittered straight line: the shape is two points, the stream is many. */
function noisyLine(count: number): { x: number; y: number }[] {
  return Array.from({ length: count }, (_, i) => ({
    x: i * 0.1,
    y: i % 2 === 0 ? 0.002 : -0.002,
  }));
}

describe('simplify', () => {
  it('reduces a jittered line to its two ends', () => {
    const result = simplify(noisyLine(200), 0.05);
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ x: 0, y: 0.002 });
    expect(result[result.length - 1]?.x).toBeCloseTo(19.9);
  });

  it('keeps a corner that a tolerance cannot explain away', () => {
    const corner = [
      { x: 0, y: 0 },
      { x: 5, y: 0.01 },
      { x: 10, y: 0 },
      { x: 10, y: 10 },
    ];
    // The near-collinear middle point goes; the right angle stays.
    expect(simplify(corner, 0.05)).toEqual([
      { x: 0, y: 0 },
      { x: 10, y: 0 },
      { x: 10, y: 10 },
    ]);
  });

  it('leaves a shape that is already simple alone', () => {
    const square = [
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 4, y: 4 },
      { x: 0, y: 4 },
    ];
    expect(simplify(square, 0.05)).toEqual(square);
  });

  it('never returns fewer than the two points it was given', () => {
    expect(simplify([{ x: 1, y: 1 }, { x: 2, y: 2 }], 10)).toHaveLength(2);
    expect(simplify([{ x: 1, y: 1 }], 10)).toHaveLength(1);
  });
});

describe('closeIfNear', () => {
  it('drops the trailing point when the hand came back near the start', () => {
    const nearly = [
      { x: 0, y: 0 },
      { x: 5, y: 0 },
      { x: 5, y: 5 },
      { x: 0.3, y: 0.2 },
    ];
    // Closing means removing the stray end, not appending the first point:
    // a polygon is already closed by being a polygon.
    expect(closeIfNear(nearly, 1)).toEqual([
      { x: 0, y: 0 },
      { x: 5, y: 0 },
      { x: 5, y: 5 },
    ]);
  });

  it('leaves an open sweep open', () => {
    const open = [
      { x: 0, y: 0 },
      { x: 5, y: 0 },
      { x: 5, y: 5 },
      { x: 5, y: 9 },
    ];
    expect(closeIfNear(open, 1)).toEqual(open);
  });

  it('does not eat a triangle down to a line', () => {
    // Three points that happen to end near the start are still a triangle;
    // dropping one would leave two, which is nothing at all.
    const tiny = [
      { x: 0, y: 0 },
      { x: 0.5, y: 0.9 },
      { x: 0.2, y: 0.1 },
    ];
    expect(closeIfNear(tiny, 1)).toHaveLength(3);
  });
});

describe('resolveOverlap', () => {
  it('turns a bow tie into the outline the hand meant', () => {
    // The classic scribble: the stroke crosses itself.
    const bowTie = [
      { x: 0, y: 0 },
      { x: 4, y: 4 },
      { x: 4, y: 0 },
      { x: 0, y: 4 },
    ];
    const fixed = resolveOverlap(bowTie);
    expect(fixed).not.toBeNull();
    expect(fixed).toHaveLength(4);
    // The four corners survive; only their order changed.
    expect(new Set(fixed?.map((p) => `${p.x},${p.y}`))).toEqual(
      new Set(['0,0', '4,4', '4,0', '0,4']),
    );
  });

  it('leaves a shape that does not cross itself untouched', () => {
    const square = [
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 4, y: 4 },
      { x: 0, y: 4 },
    ];
    expect(resolveOverlap(square)).toEqual(square);
  });

  it('keeps a concave shape concave', () => {
    // The reason this is not just a convex hull: an L-shaped bed is a normal
    // thing to draw, and a hull would fill in its notch.
    const ell = [
      { x: 0, y: 0 },
      { x: 6, y: 0 },
      { x: 6, y: 2 },
      { x: 2, y: 2 },
      { x: 2, y: 6 },
      { x: 0, y: 6 },
    ];
    expect(resolveOverlap(ell)).toEqual(ell);
  });

  it('gives up rather than inventing a shape', () => {
    // Two points cannot be an outline, and guessing one would put a bed on
    // the plan that nobody drew.
    expect(resolveOverlap([{ x: 0, y: 0 }, { x: 1, y: 1 }])).toBeNull();
  });
});

describe('tidy', () => {
  it('turns a scribbled circle into a usable outline', () => {
    // 300 points around a circle, with a hand that overshot the start.
    const scribble = Array.from({ length: 300 }, (_, i) => {
      const a = (i / 280) * Math.PI * 2;
      return { x: 3 * Math.cos(a), y: 3 * Math.sin(a) };
    });
    const result = tidy(scribble, { tolerance: 0.15, closeWithin: 1 });
    expect(result).not.toBeNull();
    expect(result!.length).toBeGreaterThan(5);
    expect(result!.length).toBeLessThan(40);
  });

  it('rounds what it returns to the centimetre', () => {
    // A hand-drawn outline is not a survey. Full float precision would store
    // 17 digits of pointer noise per corner.
    const result = tidy(
      [
        { x: 0.123456, y: 0 },
        { x: 4, y: 0 },
        { x: 4, y: 4.987654 },
      ],
      { tolerance: 0.05, closeWithin: 1 },
    );
    expect(result?.[0]?.x).toBe(0.12);
    expect(result?.[2]?.y).toBe(4.99);
  });

  it('returns null for a stroke that is not a shape', () => {
    expect(tidy([{ x: 0, y: 0 }, { x: 1, y: 0 }], { tolerance: 0.05, closeWithin: 1 }))
      .toBeNull();
  });

  it('refuses a stroke with no area rather than storing a line', () => {
    const straight = Array.from({ length: 50 }, (_, i) => ({ x: i * 0.2, y: 0 }));
    expect(tidy(straight, { tolerance: 0.05, closeWithin: 1 })).toBeNull();
  });
});

describe('traceFrom', () => {
  const loop = Array.from({ length: 120 }, (_, i) => {
    const a = (i / 119) * Math.PI * 2;
    return { x: 4 * Math.cos(a), y: 4 * Math.sin(a) };
  });
  const sweep = Array.from({ length: 60 }, (_, i) => ({ x: i * 0.3, y: 0 }));

  it('reads a closed loop as an area', () => {
    const traced = traceFrom(loop, { tolerance: 0.2, closeWithin: 1 });
    expect(traced?.kind).toBe('area');
  });

  it('reads an open stroke as a path', () => {
    // The gesture decides, not a mode: a stroke that does not come back is a
    // path, and a path is a line with a width rather than an outline.
    const traced = traceFrom(sweep, { tolerance: 0.2, closeWithin: 1 });
    expect(traced?.kind).toBe('path');
  });

  it('keeps a path open even though it has no area', () => {
    // `tidy` refuses a stroke with no area, and rightly — for an outline. A
    // path is exactly that stroke and must survive it.
    const traced = traceFrom(sweep, { tolerance: 0.2, closeWithin: 1 });
    expect(traced?.points.length).toBeGreaterThanOrEqual(2);
  });

  it('simplifies a path as it does an outline', () => {
    const jittery = Array.from({ length: 200 }, (_, i) => ({
      x: i * 0.1,
      y: i % 2 === 0 ? 0.01 : -0.01,
    }));
    const traced = traceFrom(jittery, { tolerance: 0.2, closeWithin: 1 });
    expect(traced?.points.length).toBeLessThan(10);
  });

  it('refuses a stroke too short to be either', () => {
    expect(traceFrom([{ x: 0, y: 0 }], { tolerance: 0.2, closeWithin: 1 })).toBeNull();
  });
});
