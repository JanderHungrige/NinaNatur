import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import type { DrawnShape } from '../canvas/shapes';
import { GardenCanvas } from './GardenCanvas';

function garden(): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null, share_token: 'tok', name: 'Testgarten',
    latitude: 52.5, longitude: 13.4, created_at: '', updated_at: '',
    beds: [], obstacles: [],
  };
}

const SIZE = { widthPx: 800, heightPx: 600 };
/** 800 px spanning 40 m: 20 px is a metre. */
const PX_PER_M = 20;

function drag(surface: Element, from: [number, number], to: [number, number]) {
  fireEvent.pointerDown(surface, { clientX: from[0], clientY: from[1], pointerId: 1 });
  fireEvent.pointerMove(surface, { clientX: to[0], clientY: to[1], pointerId: 1 });
  fireEvent.pointerUp(surface, { clientX: to[0], clientY: to[1], pointerId: 1 });
}

describe('GardenCanvas — drawing shapes', () => {
  function draw(tool: string) {
    const onDrawShape = vi.fn();
    render(
      <GardenCanvas
        garden={garden()}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        tool={tool as never}
        onDrawShape={onDrawShape}
      />,
    );
    return onDrawShape;
  }

  it('draws a rectangle at the size it was dragged', () => {
    const onDrawShape = draw('rect');
    // 400,300 is the centre of the plan; drag 6 m east and 4 m south.
    drag(screen.getByTestId('canvas-surface'), [400, 300], [400 + 6 * PX_PER_M, 300 + 4 * PX_PER_M]);
    expect(onDrawShape).toHaveBeenCalledTimes(1);
    const shape = onDrawShape.mock.calls[0]?.[0] as DrawnShape;
    expect(shape.shape).toBe('rect');
    expect(shape.width).toBeCloseTo(6, 1);
    expect(shape.depth).toBeCloseTo(4, 1);
    expect(shape.constraintHint).toBe('rect');
  });

  it('shows the shape while it is being dragged', () => {
    draw('circle');
    const surface = screen.getByTestId('canvas-surface');
    fireEvent.pointerDown(surface, { clientX: 400, clientY: 300, pointerId: 1 });
    fireEvent.pointerMove(surface, { clientX: 480, clientY: 380, pointerId: 1 });
    // Without a preview the user is dragging blind and only finds out on release.
    expect(screen.getByTestId('shape-preview')).toBeDefined();
    fireEvent.pointerUp(surface, { clientX: 480, clientY: 380, pointerId: 1 });
    expect(screen.queryByTestId('shape-preview')).toBeNull();
  });

  it('produces nothing from a mis-click', () => {
    const onDrawShape = draw('rect');
    drag(screen.getByTestId('canvas-surface'), [400, 300], [402, 301]);
    expect(onDrawShape).not.toHaveBeenCalled();
  });

  it('does not pan the plan while a shape is being drawn', () => {
    const onDrawShape = draw('triangle');
    const surface = screen.getByTestId('canvas-surface');
    const before = surface.getAttribute('viewBox');
    drag(surface, [300, 200], [420, 320]);
    expect(surface.getAttribute('viewBox')).toBe(before);
    expect(onDrawShape).toHaveBeenCalled();
  });

  it('pans instead of drawing when no tool is armed', () => {
    // Disarming after a shape is the parent's job — the canvas only reports
    // what was drawn. What it must get right is doing nothing when nothing is
    // armed, or the plan could never be moved again.
    const onDrawShape = vi.fn();
    render(
      <GardenCanvas
        garden={garden()} selectedBedId={null} onSelectBed={vi.fn()}
        size={SIZE} tool={null} onDrawShape={onDrawShape}
      />,
    );
    const surface = screen.getAllByTestId('canvas-surface')[0]!;
    const before = surface.getAttribute('viewBox');
    drag(surface, [300, 200], [420, 320]);
    expect(onDrawShape).not.toHaveBeenCalled();
    expect(surface.getAttribute('viewBox')).not.toBe(before);
  });

  it('abandons a drag on Escape', () => {
    const onDrawShape = draw('rect');
    const surface = screen.getByTestId('canvas-surface');
    fireEvent.pointerDown(surface, { clientX: 300, clientY: 200, pointerId: 1 });
    fireEvent.pointerMove(surface, { clientX: 420, clientY: 320, pointerId: 1 });
    fireEvent.keyDown(window, { key: 'Escape' });
    fireEvent.pointerUp(surface, { clientX: 420, clientY: 320, pointerId: 1 });
    expect(onDrawShape).not.toHaveBeenCalled();
  });
});
