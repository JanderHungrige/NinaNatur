import { describe, expect, it } from 'vitest';

import { centreline, halfWidth, lengthOf, parallel, stations } from './along';

/* Geometry along an element's own line (doc 98): a fence, a wall, a hedge. */

const line = [{ x: 0, y: 0 }, { x: 4, y: 0 }, { x: 4, y: 3 }];
/** A wall 6 m long and 0.3 m thick, running north-east. */
const wall = [{ x: 0, y: 0 }, { x: 4.243, y: 4.243 }, { x: 4.031, y: 4.455 }, { x: -0.212, y: 0.212 }];

describe('stations — where marks go along a line', () => {
  it('are every spacing from the start, turning with the line, never past its end', () => {
    const at = stations(line, 2, 1);
    expect(at.map((s) => [s.at.x, s.at.y])).toEqual([[1, 0], [3, 0], [4, 1], [4, 3]]);
    expect(at.map((s) => Math.round((s.angle * 180) / Math.PI))).toEqual([0, 0, 90, 90]);
    expect(lengthOf(line)).toBe(7);
  });
});

describe('parallel — a line moved to one side', () => {
  it('keeps its distance, left for a positive offset, right for a negative', () => {
    expect(parallel([{ x: 0, y: 0 }, { x: 4, y: 0 }], 0.5)).toEqual([{ x: 0, y: 0.5 }, { x: 4, y: 0.5 }]);
    expect(parallel([{ x: 0, y: 0 }, { x: 4, y: 0 }], -0.5)).toEqual([{ x: 0, y: -0.5 }, { x: 4, y: -0.5 }]);
    const corner = parallel(line, 0.5)[1]!;
    expect(corner.x).toBeCloseTo(3.5, 9);
    expect(corner.y).toBeCloseTo(0.5, 9);
  });
});

describe('centreline — the long axis of a thin outline', () => {
  it('runs from end to end through the middle, whichever way the wall is turned', () => {
    const [a, b] = centreline(wall);
    expect(Math.hypot(b!.x - a!.x, b!.y - a!.y)).toBeCloseTo(6, 2);
    expect(halfWidth(wall)).toBeCloseTo(0.15, 2);
    const middle = { x: (a!.x + b!.x) / 2, y: (a!.y + b!.y) / 2 };
    expect(middle.x).toBeCloseTo(2.016, 2);
    expect(middle.y).toBeCloseTo(2.228, 2);
  });
});
