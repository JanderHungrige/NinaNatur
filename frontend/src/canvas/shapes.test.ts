import { describe, expect, it } from 'vitest';

import { MIN_DRAG_M, type Tool, shapeFromDrag } from './shapes';

const FROM = { x: 0, y: 0 };

describe('shapeFromDrag', () => {
  it('spans a rectangle across the drag', () => {
    const drawn = shapeFromDrag('rect', FROM, { x: 10, y: 6 });
    expect(drawn).not.toBeNull();
    expect(drawn!.shape).toBe('rect');
    // Centred on the middle of the drag, not on where it started.
    expect(drawn!.x).toBeCloseTo(5);
    expect(drawn!.y).toBeCloseTo(3);
    expect(drawn!.width!).toBeCloseTo(10);
    expect(drawn!.depth!).toBeCloseTo(6);
  });

  it('draws a rectangle the same way when dragged backwards', () => {
    // Nobody drags only down and to the right.
    const forward = shapeFromDrag('rect', FROM, { x: 10, y: 6 });
    const backward = shapeFromDrag('rect', { x: 10, y: 6 }, FROM);
    expect(backward!.x).toBeCloseTo(forward!.x);
    expect(backward!.width!).toBeCloseTo(forward!.width!);
    expect(backward!.depth!).toBeCloseTo(forward!.depth!);
  });

  it('takes the drag as a circle diameter', () => {
    const drawn = shapeFromDrag('circle', FROM, { x: 8, y: 8 });
    expect(drawn!.shape).toBe('circle');
    expect(drawn!.width!).toBeCloseTo(8);
    expect(drawn!.points).toBeNull();
  });

  it('keeps a circle round when the drag is not square', () => {
    // A circle has one measurement. Taking the larger side would grow past
    // where the pointer went; the smaller one stays inside the gesture.
    const drawn = shapeFromDrag('circle', FROM, { x: 10, y: 4 });
    expect(drawn!.width!).toBeCloseTo(4);
  });

  it('sits a triangle in the drag', () => {
    const drawn = shapeFromDrag('triangle', FROM, { x: 6, y: 6 });
    expect(drawn!.shape).toBe('polygon');
    expect(drawn!.points).toHaveLength(3);
    // Apex at the top, base along the bottom — a triangle a gardener would draw.
    const ys = drawn!.points!.map((p) => p[1]!);
    expect(Math.max(...ys)).toBeCloseTo(3);
    expect(ys.filter((y) => Math.abs(y + 3) < 1e-6)).toHaveLength(2);
  });

  it('refuses a mis-click rather than making a speck', () => {
    expect(shapeFromDrag('rect', FROM, { x: 0.05, y: 0.05 })).toBeNull();
    expect(shapeFromDrag('circle', FROM, { x: MIN_DRAG_M / 2, y: 10 })).toBeNull();
  });

  it('rounds what it stores to the centimetre', () => {
    const drawn = shapeFromDrag('rect', FROM, { x: 3.14159, y: 2.71828 });
    expect(drawn!.width).toBe(3.14);
    expect(drawn!.depth).toBe(2.72);
  });

  it('marks a rectangle as one so its corners stay square', () => {
    const tools: Tool[] = ['rect', 'circle', 'triangle'];
    const hints = tools.map((t) => shapeFromDrag(t, FROM, { x: 8, y: 8 })!.constraintHint);
    expect(hints).toEqual(['rect', null, null]);
  });
});
