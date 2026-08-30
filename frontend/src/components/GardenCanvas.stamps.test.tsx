import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { GardenCanvas } from './GardenCanvas';

function obstacle(
  overrides: Partial<GardenOut['obstacles'][number]> = {},
): GardenOut['obstacles'][number] {
  return {
    obstacle_id: 7,
    kind: 'house',
    x: 0,
    y: 0,
    shape: 'rect',
    width: 10,
    height: 6,
    label: null,
    height_source: 'user',
    points: null,
    constraint_hint: null,
    footprint: [[-5, 4], [5, 4], [5, -4], [-5, -4]],
    ...overrides,
  };
}

function garden(overrides: Partial<GardenOut> = {}): GardenOut {
  return {
    unidentified_plantings: 0,
    share_token: 'tok',
    name: 'Testgarten',
    latitude: 52.5,
    longitude: 13.4,
    created_at: '',
    updated_at: '',
    beds: [],
    obstacles: [],
    ...overrides,
  };
}

const SIZE = { widthPx: 800, heightPx: 600 };

/**
 * Placing and sizing ready-made elements (Wave 10, feature 3).
 *
 * The canvas is told its pixel size: jsdom lays nothing out, so a measured
 * surface would convert every click to NaN metres.
 */
describe('GardenCanvas — stamps', () => {
  it('places the armed element where the user clicked', () => {
    const onPlaceStamp = vi.fn();
    render(
      <GardenCanvas
        garden={garden()}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        stampKind="house"
        onPlaceStamp={onPlaceStamp}
      />,
    );
    // The centre of an 800×600 surface spanning 40 m is garden (0, 0).
    fireEvent.click(screen.getByTestId('canvas-surface'), { clientX: 400, clientY: 300 });
    expect(onPlaceStamp).toHaveBeenCalledWith('house', 0, 0);
  });

  it('snaps a placement to the grid, and Alt places it freely', () => {
    const onPlaceStamp = vi.fn();
    render(
      <GardenCanvas
        garden={garden()}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        stampKind="tree"
        onPlaceStamp={onPlaceStamp}
      />,
    );
    const surface = screen.getByTestId('canvas-surface');
    fireEvent.click(surface, { clientX: 409, clientY: 300 });
    const [, snappedX] = onPlaceStamp.mock.calls[0] as [string, number, number];
    expect(Number.isInteger(snappedX)).toBe(true);

    fireEvent.click(surface, { clientX: 409, clientY: 300, altKey: true });
    const [, freeX] = onPlaceStamp.mock.calls[1] as [string, number, number];
    expect(freeX).not.toBe(snappedX);
  });

  it('does not place anything when nothing is armed', () => {
    const onPlaceStamp = vi.fn();
    render(
      <GardenCanvas
        garden={garden()}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        stampKind={null}
        onPlaceStamp={onPlaceStamp}
      />,
    );
    fireEvent.click(screen.getByTestId('canvas-surface'), { clientX: 400, clientY: 300 });
    expect(onPlaceStamp).not.toHaveBeenCalled();
  });

  it('gives the selected object handles to pull, each one named', () => {
    render(
      <GardenCanvas
        garden={garden({ obstacles: [obstacle()] })}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        selectedObstacleId={7}
        onResizeObstacle={vi.fn()}
      />,
    );
    // The eight of draw.io, plus the one that turns it.
    expect(screen.getAllByTestId(/^handle-(n|ne|e|se|s|sw|w|nw)$/)).toHaveLength(8);
    expect(screen.getByTestId('handle-rotate')).toBeDefined();
  });

  it('leaves an unselected object without handles', () => {
    render(
      <GardenCanvas
        garden={garden({ obstacles: [obstacle()] })}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        selectedObstacleId={null}
        onResizeObstacle={vi.fn()}
      />,
    );
    expect(screen.queryAllByTestId(/^handle-/)).toHaveLength(0);
  });

  it('reports a new size only when the drag ends', () => {
    // One save per gesture, not one per pixel: a PATCH per mousemove would
    // recompute the light of every bed dozens of times across one drag.
    const onResizeObstacle = vi.fn();
    render(
      <GardenCanvas
        garden={garden({ obstacles: [obstacle()] })}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        selectedObstacleId={7}
        onResizeObstacle={onResizeObstacle}
      />,
    );
    const handle = screen.getByTestId('handle-e');
    fireEvent.pointerDown(handle, { clientX: 500, clientY: 300 });
    fireEvent.pointerMove(window, { clientX: 540, clientY: 300 });
    expect(onResizeObstacle).not.toHaveBeenCalled();

    fireEvent.pointerUp(window, { clientX: 540, clientY: 300 });
    expect(onResizeObstacle).toHaveBeenCalledTimes(1);
    const [id, box] = onResizeObstacle.mock.calls[0] as [number, { width: number }];
    expect(id).toBe(7);
    // 40 px of an 800 px surface spanning 40 m is 2 m, pulled on one side.
    expect(box.width).toBeCloseTo(12, 1);
  });

  it('does not report a resize when the pointer never moved', () => {
    // Clicking a handle is not a resize, and a PATCH that changes nothing still
    // costs a light recomputation.
    const onResizeObstacle = vi.fn();
    render(
      <GardenCanvas
        garden={garden({ obstacles: [obstacle()] })}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        selectedObstacleId={7}
        onResizeObstacle={onResizeObstacle}
      />,
    );
    fireEvent.pointerDown(screen.getByTestId('handle-e'), { clientX: 500, clientY: 300 });
    fireEvent.pointerUp(window, { clientX: 500, clientY: 300 });
    expect(onResizeObstacle).not.toHaveBeenCalled();
  });

  it('turns the object with the rotation handle', () => {
    const onResizeObstacle = vi.fn();
    render(
      <GardenCanvas
        garden={garden({ obstacles: [obstacle()] })}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        selectedObstacleId={7}
        onResizeObstacle={onResizeObstacle}
      />,
    );
    fireEvent.pointerDown(screen.getByTestId('handle-rotate'), { clientX: 400, clientY: 200 });
    // Drag to due east of the centre: 90°.
    fireEvent.pointerMove(window, { clientX: 600, clientY: 300 });
    fireEvent.pointerUp(window, { clientX: 600, clientY: 300 });
    const [, box] = onResizeObstacle.mock.calls[0] as [number, { rotation: number }];
    expect(box.rotation).toBeCloseTo(90);
  });

  it('does not start a bed vertex while an element is armed', () => {
    // Two modes, one click. Arming a stamp must win, or the click both places a
    // house and drops a bed corner under it.
    const onDrawBed = vi.fn();
    const onPlaceStamp = vi.fn();
    render(
      <GardenCanvas
        garden={garden()}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        onDrawBed={onDrawBed}
        stampKind="lawn"
        onPlaceStamp={onPlaceStamp}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /Beet zeichnen/ }));
    fireEvent.click(screen.getByTestId('canvas-surface'), { clientX: 400, clientY: 300 });
    expect(onPlaceStamp).toHaveBeenCalled();
    expect(screen.queryByText(/1 Ecke/)).toBeNull();
  });
});
