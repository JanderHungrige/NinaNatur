import { describe, expect, it } from 'vitest';

import { MIN_VERTICES, insertVertex, midpoints, moveVertex, removeVertex } from './vertices';

const SQUARE = [[0, 0], [4, 0], [4, 4], [0, 4]];

describe('midpoints', () => {
  it('offers one insertion point per edge, including the closing one', () => {
    // Four corners make four edges. Forgetting the edge from the last corner
    // back to the first is how one side of every shape becomes uneditable.
    const mids = midpoints(SQUARE);
    expect(mids).toHaveLength(4);
    expect(mids[3]).toEqual({ index: 3, at: [0, 2] });
  });

  it('walks the ends of a line rather than closing it', () => {
    // A path is not a ring: it has no edge from its last point back to its
    // first, and offering one would put a handle in mid-air.
    expect(midpoints([[0, 0], [4, 0], [4, 4]], { closed: false })).toHaveLength(2);
  });
});

describe('insertVertex', () => {
  it('puts the new corner between the two it was drawn from', () => {
    const grown = insertVertex(SQUARE, 0);
    expect(grown).toHaveLength(5);
    expect(grown[1]).toEqual([2, 0]);
    // The corners either side are untouched.
    expect(grown[0]).toEqual([0, 0]);
    expect(grown[2]).toEqual([4, 0]);
  });

  it('closes the ring when inserting on the last edge', () => {
    const grown = insertVertex(SQUARE, 3);
    expect(grown[4]).toEqual([0, 2]);
  });
});

describe('moveVertex', () => {
  it('moves one corner and leaves the others alone', () => {
    const moved = moveVertex(SQUARE, 1, [6, -1]);
    expect(moved[1]).toEqual([6, -1]);
    expect(moved[0]).toEqual([0, 0]);
    expect(moved[3]).toEqual([0, 4]);
  });

  it('rounds to the centimetre, like everything else stored', () => {
    expect(moveVertex(SQUARE, 0, [1.23456, 2.98765])[0]).toEqual([1.23, 2.99]);
  });
});

describe('removeVertex', () => {
  it('takes a corner out', () => {
    expect(removeVertex(SQUARE, 2)).toEqual([[0, 0], [4, 0], [0, 4]]);
  });

  it('refuses to leave a shape that is not one', () => {
    // Three corners are the fewest that enclose anything. Below that the
    // element would still exist and cover nothing.
    const triangle = [[0, 0], [4, 0], [2, 3]];
    expect(triangle).toHaveLength(MIN_VERTICES);
    expect(removeVertex(triangle, 1)).toBeNull();
  });
});
