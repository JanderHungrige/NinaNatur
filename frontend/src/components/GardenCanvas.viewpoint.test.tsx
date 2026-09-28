import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { garden } from '../testing/gardens';
import { GardenCanvas } from './GardenCanvas';

const SIZE = { widthPx: 800, heightPx: 600 };

describe('GardenCanvas — Standpunkt is a tool', () => {
  it('places the viewpoint where the plan is clicked, and puts the tool down', () => {
    // Doc 89. The plan used to hold its own "placing" mode behind a button in its
    // controls; the rail's tool is the one mode now, and placing ends it.
    const onPlaceViewpoint = vi.fn();
    const onCancelTool = vi.fn();
    render(
      <GardenCanvas
        garden={garden('tok', 'G')}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        tool="viewpoint"
        onDrawBed={vi.fn()}
        onPlaceViewpoint={onPlaceViewpoint}
        onCancelTool={onCancelTool}
      />,
    );
    fireEvent.click(screen.getByTestId('canvas-surface'), { clientX: 400, clientY: 300 });
    expect(onPlaceViewpoint).toHaveBeenCalledTimes(1);
    const [x, y] = onPlaceViewpoint.mock.calls[0] as [number, number];
    expect(Number.isFinite(x) && Number.isFinite(y)).toBe(true);
    expect(onCancelTool).toHaveBeenCalled();
  });

  it('takes the click from the shapes under it while it is armed', () => {
    // Doc 49: an armed tool takes the click, and this one is no exception.
    render(
      <GardenCanvas
        garden={garden('tok', 'G')}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        tool="viewpoint"
        onPlaceViewpoint={vi.fn()}
      />,
    );
    expect(screen.queryByRole('button', { name: /Südbeet/ })).toBeNull();
  });

  it('places nothing while no tool is armed', () => {
    const onPlaceViewpoint = vi.fn();
    render(
      <GardenCanvas
        garden={garden('tok', 'G')}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        tool={null}
        onDrawBed={vi.fn()}
        onPlaceViewpoint={onPlaceViewpoint}
      />,
    );
    fireEvent.click(screen.getByTestId('canvas-surface'), { clientX: 400, clientY: 300 });
    expect(onPlaceViewpoint).not.toHaveBeenCalled();
  });
});

describe('GardenCanvas — a shadow mark is placed like a viewpoint (doc 122)', () => {
  it('places the mark where the plan is clicked while an element has armed it', () => {
    const onPlaceViewpoint = vi.fn();
    const onCancelTool = vi.fn();
    render(
      <GardenCanvas
        garden={garden('tok', 'G')}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        tool="shadowmark"
        onDrawBed={vi.fn()}
        onPlaceViewpoint={onPlaceViewpoint}
        onCancelTool={onCancelTool}
      />,
    );
    fireEvent.click(screen.getByTestId('canvas-surface'), { clientX: 400, clientY: 300 });
    expect(onPlaceViewpoint).toHaveBeenCalledTimes(1);
    expect(onCancelTool).toHaveBeenCalled();
  });

  it('takes a click on a planted patch as the mark, not as choosing the plant', () => {
    // The patches stood above the shapes and kept their clicks while a tool
    // was armed: a mark aimed at a planted bed chose the planting instead,
    // and the plan went back to the planting's details (review of stage 3,
    // 2026-09-28).
    const onPlaceViewpoint = vi.fn();
    const onSelectCluster = vi.fn();
    render(
      <GardenCanvas
        garden={garden('tok', 'G')}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        tool="shadowmark"
        onPlaceViewpoint={onPlaceViewpoint}
        clusters={[{ plantingId: 3, taxonId: 7, name: 'Salvia pratensis',
                     centre: { x: 0, y: 0 }, radius: 0.6, colour: null,
                     dots: [{ x: 0, y: 0, r: 0.1 }] }]}
        onSelectCluster={onSelectCluster}
      />,
    );
    const patch = screen.getByTestId('cluster-3');
    expect(patch.getAttribute('role')).toBeNull();
    fireEvent.click(patch, { clientX: 400, clientY: 300 });
    expect(onSelectCluster).not.toHaveBeenCalled();
    expect(onPlaceViewpoint).toHaveBeenCalledTimes(1);
  });

  it('draws the marks it is given', () => {
    const { container } = render(
      <GardenCanvas
        garden={garden('tok', 'G')}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={SIZE}
        shadowMarks={[{ mark_id: 1, element_id: 2, x: 1, y: 2,
                        seen_at: '2026-06-21T09:30:00+00:00', reading: null }]}
      />,
    );
    expect(container.querySelectorAll('.shadow-mark')).toHaveLength(1);
  });
});
