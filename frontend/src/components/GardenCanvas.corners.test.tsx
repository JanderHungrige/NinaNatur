import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { GardenCanvas } from './GardenCanvas';

function garden(): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {},
    share_token: 'tok', name: 'Testgarten', latitude: 52.5, longitude: 13.4,
    created_at: '', updated_at: '', beds: [], obstacles: [],
  };
}

type Props = Partial<Parameters<typeof GardenCanvas>[0]>;

/**
 * Where a corner lands, and what a short stroke does (the owner's check,
 * 2026-09-21, #2 and #3). 800 px across 40 m at centre (0, 0): 20 px per metre,
 * the garden's origin at (400, 300), a 1 m grid.
 */
describe('GardenCanvas — corners land where they are clicked', () => {
  function draw(props: Props = {}) {
    const onDrawBed = vi.fn();
    const onDrawTrace = vi.fn();
    const view = (more: Props) => (
      <GardenCanvas
        garden={garden()} selectedBedId={null} onSelectBed={vi.fn()}
        size={{ widthPx: 800, heightPx: 600 }} onDrawBed={onDrawBed}
        onDrawTrace={onDrawTrace} tool="polygon" {...props} {...more}
      />
    );
    const { rerender } = render(view({}));
    return { onDrawBed, onDrawTrace, rerender: (more: Props) => rerender(view(more)) };
  }

  const surface = () => screen.getByTestId('canvas-surface');
  const clickAt = (x: number, y: number) => fireEvent.click(surface(), { clientX: x, clientY: y });
  const finish = () => fireEvent.click(screen.getByRole('button', { name: 'Fertig' }));

  it('keeps a corner where it was clicked when no grid point is near', () => {
    // 10 px off the grid: it used to be pulled half a metre onto it.
    const { onDrawBed } = draw();
    clickAt(410, 300);
    clickAt(480, 300);
    clickAt(480, 220);
    finish();
    expect(onDrawBed).toHaveBeenCalledWith([[0.5, 0], [4, 0], [4, 4]]);
  });

  it('pulls a corner onto a grid point a few pixels away', () => {
    const { onDrawBed } = draw();
    clickAt(403, 302);
    clickAt(480, 300);
    clickAt(480, 220);
    finish();
    expect(onDrawBed).toHaveBeenCalledWith([[0, 0], [4, 0], [4, 4]]);
  });

  it('never pulls while Alt is held', () => {
    const { onDrawBed } = draw();
    fireEvent.click(surface(), { clientX: 403, clientY: 300, altKey: true });
    clickAt(480, 300);
    clickAt(480, 220);
    finish();
    expect(onDrawBed).toHaveBeenCalledWith([[0.15, 0], [4, 0], [4, 4]]);
  });

  it('keeps a last corner one grid square from the first', () => {
    // Closing used to reach a whole grid square: a 3 × 1 m bed became a triangle.
    const { onDrawBed } = draw();
    clickAt(400, 300);
    clickAt(460, 300);
    clickAt(460, 280);
    clickAt(400, 280);
    finish();
    expect(onDrawBed).toHaveBeenCalledWith([[0, 0], [3, 0], [3, 1], [0, 1]]);
  });

  it('forgets a half-drawn outline when another tool is picked', () => {
    const { rerender } = draw();
    clickAt(400, 300);
    clickAt(460, 300);
    expect(screen.getByTestId('draft')).toBeDefined();
    rerender({ tool: 'rect' });
    rerender({ tool: 'polygon' });
    expect(screen.queryByTestId('draft')).toBeNull();
  });

  it('sends nothing for a freehand press that barely moved, and says why', () => {
    const { onDrawTrace } = draw({ tool: 'freehand' });
    fireEvent.pointerDown(surface(), { clientX: 400, clientY: 300, pointerId: 1 });
    fireEvent.pointerMove(surface(), { clientX: 400.1, clientY: 300, pointerId: 1 });
    fireEvent.pointerUp(surface(), { clientX: 400.1, clientY: 300, pointerId: 1 });
    expect(onDrawTrace).not.toHaveBeenCalled();
    expect(screen.getByText(/zu kurz/)).toBeDefined();
  });

  it('draws a freehand path once the stroke is long enough', () => {
    const { onDrawTrace } = draw({ tool: 'freehand' });
    fireEvent.pointerDown(surface(), { clientX: 400, clientY: 300, pointerId: 1 });
    fireEvent.pointerMove(surface(), { clientX: 440, clientY: 300, pointerId: 1 });
    fireEvent.pointerUp(surface(), { clientX: 440, clientY: 300, pointerId: 1 });
    expect(onDrawTrace).toHaveBeenCalledWith({ kind: 'path', points: [[0, 0], [2, 0]] });
  });
});
