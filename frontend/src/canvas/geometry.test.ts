import { describe, expect, it } from 'vitest';

import { type Point, area, isDegenerate, selfIntersects, covers } from './geometry';

const SQUARE: Point[] = [
  { x: 0, y: 0 },
  { x: 4, y: 0 },
  { x: 4, y: 4 },
  { x: 0, y: 4 },
];

describe('a polygon that can be saved', () => {
  it('needs three distinct points', () => {
    // Two clicks and a double-click is a line, not a bed. Saved anyway it would
    // reach the area and shading code as a shape with no inside.
    expect(isDegenerate([{ x: 0, y: 0 }, { x: 1, y: 1 }])).toBe(true);
    expect(isDegenerate(SQUARE)).toBe(false);
  });

  it('rejects three points on one line', () => {
    expect(isDegenerate([{ x: 0, y: 0 }, { x: 1, y: 1 }, { x: 2, y: 2 }])).toBe(true);
  });

  it('rejects repeated clicks in the same place', () => {
    expect(isDegenerate([{ x: 1, y: 1 }, { x: 1, y: 1 }, { x: 1, y: 1 }])).toBe(true);
  });

  it('measures area the same either way round', () => {
    expect(area(SQUARE)).toBeCloseTo(16, 6);
    expect(area([...SQUARE].reverse())).toBeCloseTo(16, 6);
  });
});

describe('self-intersection', () => {
  it('spots a bow tie', () => {
    // Easy to draw by accident and impossible to shade sensibly.
    const bowTie: Point[] = [
      { x: 0, y: 0 },
      { x: 4, y: 4 },
      { x: 4, y: 0 },
      { x: 0, y: 4 },
    ];
    expect(selfIntersects(bowTie)).toBe(true);
  });

  it('leaves an ordinary shape alone', () => {
    expect(selfIntersects(SQUARE)).toBe(false);
  });

  it('does not mistake shared corners for crossings', () => {
    // Neighbouring edges always touch at their shared vertex.
    const L: Point[] = [
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 4, y: 2 },
      { x: 2, y: 2 },
      { x: 2, y: 4 },
      { x: 0, y: 4 },
    ];
    expect(selfIntersects(L)).toBe(false);
  });
});

describe('covers', () => {
  const SQUARE = [
    { x: 0, y: 0 }, { x: 4, y: 0 }, { x: 4, y: 4 }, { x: 0, y: 4 },
  ];

  it('finds a point in the middle', () => {
    expect(covers(SQUARE, { x: 2, y: 2 })).toBe(true);
  });

  it('keeps a point outside out', () => {
    expect(covers(SQUARE, { x: 6, y: 2 })).toBe(false);
    expect(covers(SQUARE, { x: 2, y: -1 })).toBe(false);
  });

  it('keeps out of the notch of an L', () => {
    // The whole reason this exists: a bounding box would say yes here.
    const ell = [
      { x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 4 },
      { x: 4, y: 4 }, { x: 4, y: 10 }, { x: 0, y: 10 },
    ];
    expect(covers(ell, { x: 2, y: 8 })).toBe(true);
    expect(covers(ell, { x: 8, y: 8 })).toBe(false);
  });
});
