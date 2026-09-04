import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { GardenCanvas } from './GardenCanvas';

function element(): GardenOut['obstacles'][number] {
  return {
    obstacle_id: 7, kind: 'other', x: 0, y: 0, shape: 'polygon',
    width: null, constraint_hint: null,
    points: [[-3, -2], [3, -2], [3, 2], [-3, 2]],
    height: null, label: null, roof: 'unknown', height_source: 'user',
    footprint: [[-3, -2], [3, -2], [3, 2], [-3, 2]],
  };
}

function garden(): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {},
    share_token: 'tok', name: 'G', latitude: 52.5, longitude: 13.4,
    created_at: '', updated_at: '', beds: [], obstacles: [element()],
  };
}

const SIZE = { widthPx: 800, heightPx: 600 };
/** 800 px over 40 m: 20 px is a metre. */
const PX = 20;

function show(props: Record<string, unknown> = {}) {
  const onMoveObstacle = vi.fn();
  render(
    <GardenCanvas
      garden={garden()} selectedBedId={null} onSelectBed={vi.fn()}
      size={SIZE} selectedObstacleId={7} onSelectObstacle={vi.fn()}
      onMoveObstacle={onMoveObstacle}
      {...props}
    />,
  );
  return onMoveObstacle;
}

describe('GardenCanvas — moving an element', () => {
  it('drags the selected element rather than the view', () => {
    // Dragging a shape used to pan the plan, which looks exactly like the
    // shape moving — while nothing about the garden had changed.
    const onMove = show();
    const shape = screen.getByRole('button', { name: /Objekt|Sonstiges/ });
    const surface = screen.getByTestId('canvas-surface');
    const before = surface.getAttribute('viewBox');

    fireEvent.pointerDown(shape, { clientX: 400, clientY: 300, pointerId: 1 });
    fireEvent.pointerMove(window, { clientX: 400 + 5 * PX, clientY: 300 - 3 * PX });
    fireEvent.pointerUp(window, { clientX: 400 + 5 * PX, clientY: 300 - 3 * PX });

    expect(surface.getAttribute('viewBox')).toBe(before);
    const [id, at] = onMove.mock.calls[0] as [number, { x: number; y: number }];
    expect(id).toBe(7);
    expect(at.x).toBeCloseTo(5, 1);
    // Screen y grows downward, garden y grows north.
    expect(at.y).toBeCloseTo(3, 1);
  });

  it('does not report a move that never happened', () => {
    // A click on a shape selects it. Saving a move of nothing would cost a
    // PATCH and a recomputation of every bed's light.
    const onMove = show();
    const shape = screen.getByRole('button', { name: /Objekt|Sonstiges/ });
    fireEvent.pointerDown(shape, { clientX: 400, clientY: 300, pointerId: 1 });
    fireEvent.pointerUp(window, { clientX: 400, clientY: 300 });
    expect(onMove).not.toHaveBeenCalled();
  });

  it('still pans when the drag starts on empty ground', () => {
    const onMove = show();
    const surface = screen.getByTestId('canvas-surface');
    const before = surface.getAttribute('viewBox');
    fireEvent.pointerDown(surface, { clientX: 100, clientY: 100, pointerId: 1 });
    fireEvent.pointerMove(surface, { clientX: 200, clientY: 100, pointerId: 1 });
    fireEvent.pointerUp(surface, { clientX: 200, clientY: 100, pointerId: 1 });
    expect(surface.getAttribute('viewBox')).not.toBe(before);
    expect(onMove).not.toHaveBeenCalled();
  });

  it('does not move anything while a drawing tool is armed', () => {
    // The armed tool owns the pointer, shapes and all.
    const onMove = show({ tool: 'rect', onDrawShape: vi.fn() });
    const surface = screen.getByTestId('canvas-surface');
    fireEvent.pointerDown(surface, { clientX: 400, clientY: 300, pointerId: 1 });
    fireEvent.pointerMove(surface, { clientX: 500, clientY: 400, pointerId: 1 });
    fireEvent.pointerUp(surface, { clientX: 500, clientY: 400, pointerId: 1 });
    expect(onMove).not.toHaveBeenCalled();
  });

  it('will not drag the ground the garden is drawn on', () => {
    // The gardener asked to keep this. It used to hold by accident — the
    // outline was a bed, and beds could not be moved because selection only
    // ever looked in `obstacles`. Wave 15 fixed that lookup, which would have
    // made the whole plot draggable as a side effect.
    const onMove = vi.fn();
    render(
      <GardenCanvas
        garden={{
          ...garden(),
          obstacles: [{ ...element(), obstacle_id: 3, kind: 'garden' }],
        }}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={{ widthPx: 800, heightPx: 600 }}
        onMoveObstacle={onMove}
      />,
    );

    const ground = document.querySelector('[data-element-id="3"]');
    expect(ground).not.toBeNull();
    fireEvent.pointerDown(ground!, { clientX: 10, clientY: 10 });
    fireEvent.pointerMove(window, { clientX: 60, clientY: 60 });
    fireEvent.pointerUp(window, { clientX: 60, clientY: 60 });

    expect(onMove).not.toHaveBeenCalled();
  });
});
