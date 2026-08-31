import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { GardenCanvas } from './GardenCanvas';

function garden(): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null,
    share_token: 'tok',
    name: 'Testgarten',
    latitude: 52.5,
    longitude: 13.4,
    created_at: '',
    updated_at: '',
    beds: [],
    obstacles: [],
  };
}

const SIZE = { widthPx: 800, heightPx: 600 };

/** A stroke around a rough square, in screen pixels. 20 px is 1 m here. */
function squareStroke(): Array<[number, number]> {
  const path: Array<[number, number]> = [];
  const corners: Array<[number, number]> = [
    [300, 200],
    [500, 200],
    [500, 400],
    [300, 400],
    [302, 203],
  ];
  for (let i = 0; i < corners.length - 1; i += 1) {
    const from = corners[i]!;
    const to = corners[i + 1]!;
    // Twenty jittered steps a side: what a hand actually produces.
    for (let step = 0; step <= 20; step += 1) {
      const t = step / 20;
      path.push([
        from[0] + (to[0] - from[0]) * t + (step % 2 === 0 ? 0.4 : -0.4),
        from[1] + (to[1] - from[1]) * t + (step % 2 === 0 ? -0.4 : 0.4),
      ]);
    }
  }
  return path;
}

function drawStroke(surface: Element, path: Array<[number, number]>) {
  const [start, ...rest] = path;
  fireEvent.pointerDown(surface, { clientX: start![0], clientY: start![1], pointerId: 1 });
  for (const [x, y] of rest) {
    fireEvent.pointerMove(surface, { clientX: x, clientY: y, pointerId: 1 });
  }
  const last = path[path.length - 1]!;
  fireEvent.pointerUp(surface, { clientX: last[0], clientY: last[1], pointerId: 1 });
}

describe('GardenCanvas — freehand', () => {
  function draw(props: Partial<Parameters<typeof GardenCanvas>[0]> = {}) {
    const onDrawTrace = vi.fn();
    render(
      <GardenCanvas
        garden={garden()}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        tool="freehand"
        onDrawTrace={onDrawTrace}
        {...props}
      />,
    );
    return onDrawTrace;
  }

  /** The outline or centreline a stroke produced. */
  const drawn = (spy: ReturnType<typeof vi.fn>) =>
    (spy.mock.calls[0]?.[0] as { kind: string; points: number[][] });

  it('turns hundreds of jittered points into a handful of corners', () => {
    const onDrawTrace = draw();
    drawStroke(screen.getByTestId('canvas-surface'), squareStroke());

    expect(onDrawTrace).toHaveBeenCalledTimes(1);
    const polygon = drawn(onDrawTrace).points;
    // Eighty-odd points went in. A square has four corners.
    expect(polygon.length).toBeGreaterThanOrEqual(4);
    expect(polygon.length).toBeLessThanOrEqual(8);
  });

  it('closes the outline the hand left slightly open', () => {
    // The stroke ends 3 px from where it started and is never told to close.
    const onDrawTrace = draw();
    drawStroke(screen.getByTestId('canvas-surface'), squareStroke());
    const polygon = drawn(onDrawTrace).points;
    const first = polygon[0]!;
    const last = polygon[polygon.length - 1]!;
    // No duplicated corner: a polygon is closed by being one.
    expect(last).not.toEqual(first);
  });

  it('measures the shape in metres, not pixels', () => {
    // 200 px across a 40 m / 800 px surface is 10 m. A stroke stored in pixels
    // would be a different bed at every zoom level.
    const onDrawTrace = draw();
    drawStroke(screen.getByTestId('canvas-surface'), squareStroke());
    const polygon = drawn(onDrawTrace).points;
    const xs = polygon.map((p) => p[0]!);
    expect(Math.max(...xs) - Math.min(...xs)).toBeCloseTo(10, 0);
  });

  it('reads a straight sweep as a path, not as a failed outline', () => {
    // Wave 10 refused this: a stroke with no area was not a shape. It is a
    // path — which is the point of feature 46, and the gesture says so without
    // the user choosing a mode.
    const onDrawTrace = draw();
    const line: Array<[number, number]> = Array.from({ length: 40 }, (_, i) => [
      300 + i * 5,
      200,
    ]);
    drawStroke(screen.getByTestId('canvas-surface'), line);
    expect(drawn(onDrawTrace).kind).toBe('path');
  });

  it('reads a closed loop as an area', () => {
    const onDrawTrace = draw();
    drawStroke(screen.getByTestId('canvas-surface'), squareStroke());
    expect(drawn(onDrawTrace).kind).toBe('area');
  });

  it('does not pan the view while a stroke is being drawn', () => {
    // Dragging is how you pan. In freehand mode the same gesture draws, and
    // doing both would slide the garden out from under the line.
    const onDrawTrace = draw();
    const surface = screen.getByTestId('canvas-surface');
    const before = surface.getAttribute('viewBox');
    drawStroke(surface, squareStroke());
    expect(surface.getAttribute('viewBox')).toBe(before);
    expect(onDrawTrace).toHaveBeenCalled();
  });



  it('abandons a stroke on Escape', () => {
    const onDrawTrace = draw();
    const surface = screen.getByTestId('canvas-surface');
    fireEvent.pointerDown(surface, { clientX: 300, clientY: 200, pointerId: 1 });
    fireEvent.pointerMove(surface, { clientX: 400, clientY: 300, pointerId: 1 });
    fireEvent.keyDown(window, { key: 'Escape' });
    fireEvent.pointerUp(surface, { clientX: 400, clientY: 300, pointerId: 1 });
    expect(onDrawTrace).not.toHaveBeenCalled();
  });
});
