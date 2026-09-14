import { describe, expect, it } from 'vitest';

import { type Viewport, measuredView, viewBox } from './viewport';

/** 40 m across in an 800×600 window, centred on the origin. */
const V: Viewport = { centreX: 0, centreY: 0, spanM: 40, widthPx: 800, heightPx: 600 };

/** Height over width of a viewBox string. */
function shapeOf(box: string): number {
  const [, , width, height] = box.split(' ').map(Number);
  return (height ?? Number.NaN) / (width ?? Number.NaN);
}

describe('a measurement that is not one', () => {
  it('leaves the view as it was when the stage has not been laid out', () => {
    // A hidden or not-yet-laid-out box measures zero. Taking that as a size is
    // how one bad frame used to become the plan's shape until the next reload.
    expect(measuredView(V, { width: 0, height: 0 })).toBe(V);
    expect(measuredView(V, { width: 900, height: 0 })).toBe(V);
    expect(measuredView(V, { width: Number.NaN, height: 320 })).toBe(V);
  });

  it('takes a real measurement exactly, however short and wide, and draws in that shape', () => {
    // No floor under a real box: a viewBox shaped unlike the box it is drawn in
    // letterboxes the drawing and moves every click off the metre it points at.
    const next = measuredView(V, { width: 1400, height: 330 });
    expect(next).toEqual({ ...V, widthPx: 1400, heightPx: 330 });
    expect(shapeOf(viewBox(next))).toBeCloseTo(330 / 1400, 9);
  });

  it('hands back the same view when nothing changed, so there is nothing to redraw', () => {
    expect(measuredView(V, { width: 800, height: 600 })).toBe(V);
  });
});

describe('the viewBox', () => {
  it('never becomes a strip when there is no size to go by', () => {
    expect(shapeOf(viewBox({ ...V, heightPx: 0 }))).toBeGreaterThanOrEqual(0.3);
    const noWidth = shapeOf(viewBox({ ...V, widthPx: 0 }));
    expect(Number.isFinite(noWidth)).toBe(true);
    expect(noWidth).toBeGreaterThanOrEqual(0.3);
  });
});
