import { describe, expect, it } from 'vitest';

import {
  type Box,
  HANDLES,
  boxOf,
  rescale,
  handleAt,
  resizeBy,
  rotateBy,
} from './handles';

const BOX: Box = { x: 0, y: 0, width: 10, depth: 6, rotation: 0 };

describe('resize handles', () => {
  it('keeps a round shape round', () => {
    // A pond has a diameter. Pulling its east handle must grow it in both
    // directions, or the preview shows a rectangle the server will not store.
    const round = resizeBy(
      { x: 0, y: 0, width: 3, depth: 3, rotation: 0 },
      'e',
      { dx: 5, dy: 0 },
      { keepSquare: true },
    );
    expect(round.width).toBeCloseTo(8);
    expect(round.depth).toBeCloseTo(8);
  });

  it('offers a handle at each corner and each edge', () => {
    // draw.io's eight. Fewer and a user cannot pull one side; more and they
    // cannot hit any of them.
    expect(HANDLES).toHaveLength(8);
  });

  it('places the east handle on the east edge', () => {
    const east = handleAt(BOX, 'e');
    expect(east.x).toBeCloseTo(5);
    expect(east.y).toBeCloseTo(0);
  });

  it('moves the handles with the rotation', () => {
    // A rotated house has rotated handles, or dragging one moves the wrong side.
    const east = handleAt({ ...BOX, rotation: 90 }, 'e');
    expect(east.x).toBeCloseTo(0, 6);
    expect(east.y).toBeCloseTo(-5, 6);
  });

  it('widens when the east handle is dragged east', () => {
    const box = resizeBy(BOX, 'e', { dx: 2, dy: 0 });
    expect(box.width).toBeCloseTo(12);
    expect(box.depth).toBeCloseTo(6);
  });

  it('keeps the opposite edge still', () => {
    // Dragging east must not move the west wall, or the house walks away.
    const box = resizeBy(BOX, 'e', { dx: 2, dy: 0 });
    expect(box.x - box.width / 2).toBeCloseTo(BOX.x - BOX.width / 2);
  });

  it('resizes both axes from a corner', () => {
    const box = resizeBy(BOX, 'ne', { dx: 2, dy: 2 });
    expect(box.width).toBeCloseTo(12);
    expect(box.depth).toBeCloseTo(8);
  });

  it('refuses to turn a shape inside out', () => {
    // Dragging the east edge past the west one is a mis-drag, not a request for
    // a negative house.
    const box = resizeBy(BOX, 'e', { dx: -50, dy: 0 });
    expect(box.width).toBeGreaterThan(0);
  });

  it('drags along the object rotation, not the screen', () => {
    // On a house turned 90°, pulling its own east handle east must widen it
    // along its own axis.
    const turned: Box = { ...BOX, rotation: 90 };
    const box = resizeBy(turned, 'e', { dx: 0, dy: -2 });
    expect(box.width).toBeCloseTo(12, 6);
  });

  it('rotates to the angle the pointer is at', () => {
    // Pointer due east of the centre means the object faces east: 90°.
    expect(rotateBy(BOX, { x: 5, y: 0 })).toBeCloseTo(90);
  });

  it('snaps rotation to 15° steps unless asked otherwise', () => {
    // atan2(5, 1.5) is 73.3°, which snaps to 75 and stays 73.3 when free.
    expect(rotateBy(BOX, { x: 5, y: 1.5 })).toBeCloseTo(75);
    expect(rotateBy(BOX, { x: 5, y: 1.5 }, { free: true })).toBeCloseTo(73.3, 1);
  });

  it('gives north as zero', () => {
    expect(rotateBy(BOX, { x: 0, y: 5 })).toBeCloseTo(0);
  });
});

describe('boxOf', () => {
  it('reads a rectangle back out of its four corners', () => {
    // Wave 11 stores points, not a width and an angle. The handles still need
    // the box, so it is derived — and it has to survive the round trip or a
    // resize would nudge the shape every time it is selected.
    const box = boxOf({
      shape: 'polygon',
      x: 3,
      y: 4,
      width: null,
      constraint_hint: 'rect',
      points: [[-5, -4], [5, -4], [5, 4], [-5, 4]],
      footprint: [[-2, 0], [8, 0], [8, 8], [-2, 8]],
    });
    expect(box.x).toBeCloseTo(3);
    expect(box.y).toBeCloseTo(4);
    expect(box.width).toBeCloseTo(10);
    expect(box.depth).toBeCloseTo(8);
    expect(box.rotation).toBeCloseTo(0);
  });

  it('recovers the angle of a turned rectangle', () => {
    const turned = [
      [0, -5], [4, 0], [0, 5], [-4, 0],
    ];
    const box = boxOf({
      shape: 'polygon', x: 0, y: 0, width: null, constraint_hint: 'rect',
      points: turned, footprint: turned,
    });
    // The first edge runs 4 east and 5 north, so the box is turned off north.
    expect(box.width).toBeCloseTo(Math.hypot(4, 5));
    expect(box.rotation).not.toBeCloseTo(0);
  });

  it('treats a circle as square, because it is', () => {
    const box = boxOf({
      shape: 'circle', x: 2, y: 1, width: 6, constraint_hint: null,
      points: null, footprint: [[2, 4], [5, 1], [2, -2], [-1, 1]],
    });
    expect(box.width).toBeCloseTo(6);
    expect(box.depth).toBeCloseTo(6);
    expect(box.rotation).toBe(0);
  });

  it('falls back to the bounding box of a free shape', () => {
    // A freehand outline has no width and no angle to recover. The handles
    // still have to sit somewhere sensible.
    const box = boxOf({
      shape: 'polygon', x: 0, y: 0, width: null, constraint_hint: null,
      points: [[0, 0], [6, 1], [4, 5], [-1, 3]],
      footprint: [[0, 0], [6, 1], [4, 5], [-1, 3]],
    });
    expect(box.width).toBeCloseTo(7);
    expect(box.depth).toBeCloseTo(5);
    expect(box.rotation).toBe(0);
  });
});

describe('rescale', () => {
  const TRIANGLE = [[0, 3], [3, -3], [-3, -3]];
  const FROM: Box = { x: 0, y: 0, width: 6, depth: 6, rotation: 0 };

  it('scales every corner, so a triangle stays a triangle', () => {
    // Dragging a handle used to send a width and a depth, which for a shape
    // that has neither meant its points were thrown away — and the garden then
    // could not be read at all.
    const bigger = rescale(TRIANGLE, FROM, { ...FROM, width: 12, depth: 6 });
    expect(bigger).toHaveLength(3);
    expect(bigger[0]).toEqual([0, 3]);
    expect(bigger[1]).toEqual([6, -3]);
    expect(bigger[2]).toEqual([-6, -3]);
  });

  it('scales the two directions independently', () => {
    const taller = rescale(TRIANGLE, FROM, { ...FROM, width: 6, depth: 12 });
    expect(taller[0]).toEqual([0, 6]);
  });

  it('turns the corners when the box turns', () => {
    const square = [[-2, -2], [2, -2], [2, 2], [-2, 2]];
    const turned = rescale(square, { x: 0, y: 0, width: 4, depth: 4, rotation: 0 }, {
      x: 0, y: 0, width: 4, depth: 4, rotation: 90,
    });
    // A quarter turn clockwise from north: the corner that was north-east is
    // now south-east.
    expect(turned[1]?.[0]).toBeCloseTo(-2);
    expect(turned[1]?.[1]).toBeCloseTo(-2);
  });

  it('rounds to the centimetre like every other stored coordinate', () => {
    const odd = rescale([[1, 1]], FROM, { ...FROM, width: 6.13579, depth: 6 });
    expect(odd[0]?.[0]).toBe(1.02);
  });

  it('leaves the shape alone when the box has no size to scale from', () => {
    // A degenerate box would otherwise divide by zero and send NaN to the
    // server, which stores it and then cannot draw the garden.
    const same = rescale(TRIANGLE, { ...FROM, width: 0, depth: 0 }, FROM);
    expect(same).toEqual(TRIANGLE);
  });
});
