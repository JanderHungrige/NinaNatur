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
