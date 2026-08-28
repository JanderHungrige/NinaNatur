import { describe, expect, it } from 'vitest';

import {
  MAX_SPAN_M,
  MIN_SPAN_M,
  type Viewport,
  gridSpacing,
  toGarden,
  toScreen,
  viewBox,
  zoomAt,
} from './viewport';

/** 40 m across in an 800×600 window, centred on the origin. */
const V: Viewport = { centreX: 0, centreY: 0, spanM: 40, widthPx: 800, heightPx: 600 };

describe('the transform', () => {
  it('puts the centre of the garden in the centre of the window', () => {
    expect(toScreen({ x: 0, y: 0 }, V)).toEqual({ x: 400, y: 300 });
  });

  it('puts north up', () => {
    // Garden y grows north; screen y grows down. Getting this backwards would
    // mirror every shadow in the solar model.
    const north = toScreen({ x: 0, y: 10 }, V);
    expect(north.y).toBeLessThan(300);
  });

  it('round-trips a point through both directions', () => {
    const point = { x: 3.5, y: -7.25 };
    const back = toGarden(toScreen(point, V), V);
    expect(back.x).toBeCloseTo(point.x, 6);
    expect(back.y).toBeCloseTo(point.y, 6);
  });

  it('keeps metres square regardless of window shape', () => {
    // A metre east and a metre north must be the same number of pixels, or the
    // grid is rectangles and the scale bar lies.
    const wide: Viewport = { ...V, widthPx: 1200, heightPx: 300 };
    const origin = toScreen({ x: 0, y: 0 }, wide);
    const east = toScreen({ x: 1, y: 0 }, wide);
    const north = toScreen({ x: 0, y: 1 }, wide);
    expect(Math.abs(east.x - origin.x)).toBeCloseTo(Math.abs(north.y - origin.y), 6);
  });
});

describe('zoom', () => {
  it('keeps the metre under the pointer under the pointer', () => {
    // Zooming to the centre instead makes a user chase their garden across the
    // screen with every scroll.
    const pointer = { x: 600, y: 200 };
    const before = toGarden(pointer, V);
    const after = zoomAt(V, pointer, 0.5);
    const now = toGarden(pointer, after);
    expect(now.x).toBeCloseTo(before.x, 6);
    expect(now.y).toBeCloseTo(before.y, 6);
  });

  it('zooming in shows fewer metres', () => {
    expect(zoomAt(V, { x: 400, y: 300 }, 0.5).spanM).toBeLessThan(V.spanM);
  });

  it('clamps so the grid can stay honest', () => {
    const tooFar = zoomAt({ ...V, spanM: MAX_SPAN_M }, { x: 400, y: 300 }, 4);
    const tooClose = zoomAt({ ...V, spanM: MIN_SPAN_M }, { x: 400, y: 300 }, 0.01);
    expect(tooFar.spanM).toBe(MAX_SPAN_M);
    expect(tooClose.spanM).toBe(MIN_SPAN_M);
  });

  it('does not drift the centre when zooming on it', () => {
    const zoomed = zoomAt(V, { x: 400, y: 300 }, 0.5);
    expect(zoomed.centreX).toBeCloseTo(0, 9);
    expect(zoomed.centreY).toBeCloseTo(0, 9);
  });
});

describe('the grid', () => {
  it('is one metre when a metre is worth looking at', () => {
    expect(gridSpacing(V)).toBe(1);
  });

  it('stops claiming metres once they are a grey wash', () => {
    // 400 m across in 800 px is 2 px per metre. Drawing every metre there is
    // not a grid, it is a fill that still says "1 m".
    expect(gridSpacing({ ...V, spanM: 400 })).toBeGreaterThan(1);
  });

  it('steps through spacings a person would use', () => {
    const spacings = [10, 40, 200, 900].map((spanM) => gridSpacing({ ...V, spanM }));
    expect(spacings).toEqual([...spacings].sort((a, b) => a - b));
    for (const s of spacings) expect([1, 5, 25, 100]).toContain(s);
  });
});

describe('viewBox', () => {
  it('describes the same window the transform does', () => {
    const box = viewBox(V).split(' ').map(Number) as [number, number, number, number];
    const topLeft = toGarden({ x: 0, y: 0 }, V);
    expect(box[0]).toBeCloseTo(topLeft.x, 6);
    expect(box[2]).toBeCloseTo(V.spanM, 6);
  });
});
