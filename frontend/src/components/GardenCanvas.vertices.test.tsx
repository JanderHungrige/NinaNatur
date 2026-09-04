import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { GardenCanvas } from './GardenCanvas';

function element(overrides: Partial<GardenOut['obstacles'][number]> = {}) {
  return {
    obstacle_id: 7, kind: 'bed', x: 0, y: 0, shape: 'polygon',
    width: null, constraint_hint: 'rect' as string | null,
    points: [[-2, -2], [2, -2], [2, 2], [-2, 2]],
    height: null, label: null, height_source: 'user',
    footprint: [[-2, -2], [2, -2], [2, 2], [-2, 2]],
    ...overrides,
  } as GardenOut['obstacles'][number];
}

function garden(obstacles: GardenOut['obstacles']): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {}, share_token: 'tok', name: 'G', latitude: 52.5,
    longitude: 13.4, created_at: '', updated_at: '', beds: [], obstacles,
  };
}

function show(props: Record<string, unknown> = {}) {
  const onReshapeObstacle = vi.fn();
  render(
    <GardenCanvas
      garden={garden([element()])}
      selectedBedId={null}
      onSelectBed={vi.fn()}
      size={{ widthPx: 800, heightPx: 600 }}
      selectedObstacleId={7}
      onReshapeObstacle={onReshapeObstacle}
      {...props}
    />,
  );
  return onReshapeObstacle;
}

describe('GardenCanvas — editing an outline', () => {
  it('puts a handle on every corner and between every pair', () => {
    show();
    expect(screen.getAllByTestId(/^vertex-\d+$/)).toHaveLength(4);
    // Four corners make four edges, including the one that closes the ring.
    expect(screen.getAllByTestId(/^vertex-add-\d+$/)).toHaveLength(4);
  });

  it('adds a corner when an insertion point is clicked', () => {
    const onReshape = show();
    fireEvent.click(screen.getByTestId('vertex-add-0'));
    const [id, points] = onReshape.mock.calls[0] as [number, number[][]];
    expect(id).toBe(7);
    expect(points).toHaveLength(5);
    expect(points[1]).toEqual([0, -2]);
  });

  it('removes a corner on a double click', () => {
    const onReshape = show();
    fireEvent.doubleClick(screen.getByTestId('vertex-2'));
    expect((onReshape.mock.calls[0]?.[1] as number[][])).toHaveLength(3);
  });

  it('will not take a shape below three corners', () => {
    // What is left would still be an element and would cover nothing.
    const onReshape = show({
      garden: garden([element({ points: [[0, 0], [3, 0], [1, 3]] })]),
    });
    fireEvent.doubleClick(screen.getByTestId('vertex-1'));
    expect(onReshape).not.toHaveBeenCalled();
  });

  it('saves a dragged corner once the pointer is let go', () => {
    const onReshape = show();
    fireEvent.pointerDown(screen.getByTestId('vertex-1'), { clientX: 440, clientY: 340 });
    fireEvent.pointerMove(window, { clientX: 480, clientY: 340 });
    expect(onReshape).not.toHaveBeenCalled();
    fireEvent.pointerUp(window, { clientX: 480, clientY: 340 });
    expect(onReshape).toHaveBeenCalledTimes(1);
  });

  it('does not save a corner that was only clicked', () => {
    const onReshape = show();
    fireEvent.pointerDown(screen.getByTestId('vertex-0'), { clientX: 400, clientY: 300 });
    fireEvent.pointerUp(window, { clientX: 400, clientY: 300 });
    expect(onReshape).not.toHaveBeenCalled();
  });

  it('leaves a circle alone — it has no corners to edit', () => {
    show({
      garden: garden([element({ shape: 'circle', points: null, width: 4 })]),
    });
    expect(screen.queryAllByTestId(/^vertex-/)).toHaveLength(0);
  });

  it('does not close a line: a path has two ends', () => {
    show({
      garden: garden([
        element({ shape: 'line', width: 1, points: [[0, 0], [4, 0], [4, 4]] }),
      ]),
    });
    expect(screen.getAllByTestId(/^vertex-\d+$/)).toHaveLength(3);
    expect(screen.getAllByTestId(/^vertex-add-\d+$/)).toHaveLength(2);
  });

  it('gives a bed the same handles, though the API lists it separately', () => {
    // Wave 15. The server has had one `element` table since Wave 11, but the
    // API still answers with `beds` and `obstacles` apart, and selection looked
    // only in `obstacles`. So the moment somebody labelled a shape
    // "Blumenbeet" it moved across and stopped being reshapeable — the plan
    // still drew it, which is what made this look like a rendering quirk
    // rather than a lost capability.
    const bed = {
      bed_id: 7, kind: 'bed', name: 'Staudenbeet', shape: 'polygon',
      x: 0, y: 0, points: [[-2, -2], [2, -2], [2, 2], [-2, 2]],
      width: null, constraint_hint: null,
      polygon: [[-2, -2], [2, -2], [2, 2], [-2, 2]],
      soil_type: null, moisture: null, ellenberg_l: null, ellenberg_m: null,
      ellenberg_n: null, ellenberg_r: null, sun_hours: null,
      light_computed_at: null, height_above_ground: 0, label: null,
      plantings: [],
    } as unknown as GardenOut['beds'][number];

    render(
      <GardenCanvas
        garden={{ ...garden([]), beds: [bed] }}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={{ widthPx: 800, heightPx: 600 }}
        selectedObstacleId={7}
        onReshapeObstacle={vi.fn()}
        onResizeObstacle={vi.fn()}
      />,
    );

    expect(screen.getAllByTestId(/^vertex-\d+$/)).toHaveLength(4);
  });
});
