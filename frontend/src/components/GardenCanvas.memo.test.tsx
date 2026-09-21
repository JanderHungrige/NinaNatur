import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut, LightMap } from '../api/client';
import { GardenCanvas } from './GardenCanvas';

const drawn = vi.hoisted(() => ({ count: 0 }));

vi.mock('./PlanObjects', async (original) => {
  const actual = await original<typeof import('./PlanObjects')>();
  return {
    ...actual,
    PlanObjects: (props: Parameters<typeof actual.PlanObjects>[0]) => {
      drawn.count += 1;
      return actual.PlanObjects(props);
    },
  };
});

function garden(): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {},
    share_token: 'tok', name: 'Testgarten', latitude: 52.5, longitude: 13.4,
    created_at: '', updated_at: '', beds: [], obstacles: [],
  };
}

const LIGHT = {
  cell_m: 1, min_x: -20, min_y: -20, cols: 40, rows: 40,
  hours: Array.from({ length: 1600 }, (_, i) => (i % 7) + 1),
  roof: Array.from({ length: 1600 }, () => false),
  morning: Array.from({ length: 1600 }, () => 1),
  max_hours: 7, computed_at: '2026-09-21T10:00:00+00:00', stale: false, misplaced: [],
} as unknown as LightMap;

/**
 * The owner's check, 2026-09-21, #11: "everything is quite laggy, especially
 * zooming and dragging the map". Every pan frame, zoom step and — with the
 * shade on — every mouse move re-rendered the whole scene. Now they redraw the
 * backdrop, and the shapes are left alone.
 */
describe('GardenCanvas — moving the view leaves the shapes alone', () => {
  function mounted(sunMap?: { map: LightMap; mode: 'hours' }) {
    const onSelectBed = vi.fn();
    // Wired as the real plan wires it (`PlanArea`): with a move handler the
    // scene is handed the element drag's `grab`, which must stay one function.
    const view = render(
      <GardenCanvas garden={garden()} selectedBedId={null} onSelectBed={onSelectBed}
                    size={{ widthPx: 800, heightPx: 600 }} sunMap={sunMap}
                    onMoveObstacle={vi.fn()} onMoveCluster={vi.fn()} onSelectObstacle={vi.fn()} />,
    );
    return { svg: screen.getByTestId('canvas-surface'), rerender: view.rerender };
  }

  it('does not redraw the shapes on a pan', () => {
    const { svg } = mounted();
    const before = drawn.count;
    const viewBox = svg.getAttribute('viewBox');
    fireEvent.pointerDown(svg, { clientX: 400, clientY: 300 });
    for (let x = 410; x <= 480; x += 10) fireEvent.pointerMove(svg, { clientX: x, clientY: 300 });
    fireEvent.pointerUp(svg, { clientX: 480, clientY: 300 });
    expect(svg.getAttribute('viewBox')).not.toBe(viewBox);
    expect(drawn.count).toBe(before);
  });

  it('does not redraw the shapes on a wheel', () => {
    // Small steps: a zoom that crosses a halving of the scale does redraw,
    // because the level of detail changes there (`planScale`).
    const { svg } = mounted();
    const before = drawn.count;
    const viewBox = svg.getAttribute('viewBox');
    fireEvent.wheel(svg, { deltaY: -10, clientX: 400, clientY: 300 });
    fireEvent.wheel(svg, { deltaY: -10, clientX: 400, clientY: 300 });
    expect(svg.getAttribute('viewBox')).not.toBe(viewBox);
    expect(drawn.count).toBe(before);
  });

  it('does not redraw the shapes when the pointer only passes over the sun map', () => {
    const { svg } = mounted({ map: LIGHT, mode: 'hours' });
    const before = drawn.count;
    fireEvent.pointerMove(svg, { clientX: 300, clientY: 200 });
    fireEvent.pointerMove(svg, { clientX: 310, clientY: 210 });
    expect(screen.getByTestId('sun-readout')).toBeDefined();
    expect(drawn.count).toBe(before);
  });

  it('draws the sun map as a few paths, not a rect per cell', () => {
    const { svg } = mounted({ map: LIGHT, mode: 'hours' });
    const cells = svg.querySelectorAll('.sun-map__cell');
    expect(cells.length).toBeGreaterThan(0);
    expect(cells.length).toBeLessThanOrEqual(20);
    expect(svg.querySelectorAll('.sun-map rect')).toHaveLength(0);
  });
});
