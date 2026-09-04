import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { GardenCanvas } from './GardenCanvas';

function garden(): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {},
    share_token: 'tok', name: 'G', latitude: 52.5, longitude: 13.4,
    created_at: '', updated_at: '',
    beds: [{
      bed_id: 1, name: 'Gesamtfläche',
      // Wave 15: a bed carries the same geometry an obstacle does.
      kind: 'bed',
      shape: 'polygon',
      x: 0,
      y: 0,
      points: null,
      width: null,
      constraint_hint: null,
      polygon: [[-20, -20], [20, -20], [20, 20], [-20, 20]],
      soil_type: 'loam', moisture: 'fresh', ellenberg_l: null, ellenberg_m: null,
      ellenberg_n: null, ellenberg_r: null, sun_hours: null,
      light_computed_at: null, height_above_ground: 0, label: null, plantings: [],
    }],
    obstacles: [],
  };
}

const SIZE = { widthPx: 800, heightPx: 600 };

describe('GardenCanvas — an armed tool takes the click', () => {
  it('does not select the bed under the pointer while a tool is armed', () => {
    // The reported bug: the first click on the canvas selected the garden-wide
    // bed and scrolled the page to the plant suggestions, so the tool looked
    // like it needed two attempts.
    const onSelectBed = vi.fn();
    render(
      <GardenCanvas
        garden={garden()} selectedBedId={null} onSelectBed={onSelectBed}
        size={SIZE} tool="rect" onDrawShape={vi.fn()}
      />,
    );
    // Not a button while a tool is armed: the handler is left off rather than
    // covered over, so nothing can click through to it.
    expect(screen.queryByRole('button', { name: /Gesamtfläche/ })).toBeNull();
    expect(onSelectBed).not.toHaveBeenCalled();
  });

  it('selects normally when no tool is armed', () => {
    const onSelectBed = vi.fn();
    render(
      <GardenCanvas
        garden={garden()} selectedBedId={null} onSelectBed={onSelectBed}
        size={SIZE} tool={null}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /Gesamtfläche/ }));
    expect(onSelectBed).toHaveBeenCalledWith(1);
  });

  it('puts the tool down on Escape', () => {
    const onCancelTool = vi.fn();
    render(
      <GardenCanvas
        garden={garden()} selectedBedId={null} onSelectBed={vi.fn()}
        size={SIZE} tool="polygon" onDrawBed={vi.fn()} onCancelTool={onCancelTool}
      />,
    );
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onCancelTool).toHaveBeenCalled();
  });

  it('clears the selected element on Escape', () => {
    // One key for getting out of everything. Without it a selection outlives
    // whatever the user was doing and its handles stay on the plan.
    const onClearSelection = vi.fn();
    render(
      <GardenCanvas
        garden={garden()} selectedBedId={null} onSelectBed={vi.fn()}
        size={SIZE} tool={null} onClearSelection={onClearSelection}
      />,
    );
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClearSelection).toHaveBeenCalled();
  });

  it('shows the drawing controls only while a tool is armed', () => {
    const { rerender } = render(
      <GardenCanvas
        garden={garden()} selectedBedId={null} onSelectBed={vi.fn()}
        size={SIZE} tool="polygon" onDrawBed={vi.fn()}
      />,
    );
    expect(screen.queryByRole('button', { name: 'Fertig' })).not.toBeNull();
    rerender(
      <GardenCanvas
        garden={garden()} selectedBedId={null} onSelectBed={vi.fn()}
        size={SIZE} tool={null} onDrawBed={vi.fn()}
      />,
    );
    expect(screen.queryByRole('button', { name: 'Fertig' })).toBeNull();
  });

  it('does not offer the ground as anything to click', () => {
    // The garden outline is the paper, not a thing on it. The gardener asked
    // for this outright: visible, and otherwise not there as far as the pointer
    // and the keyboard are concerned. It stays an element on the server, which
    // is what sums over it.
    const onSelectObstacle = vi.fn();
    const ground = {
      obstacle_id: 3, kind: 'garden', x: 0, y: 0, shape: 'polygon',
      width: null, constraint_hint: null, points: [[-10, -10], [10, -10], [10, 10], [-10, 10]],
      height: null, label: 'Mein Garten', height_source: 'user',
      footprint: [[-10, -10], [10, -10], [10, 10], [-10, 10]],
    } as GardenOut['obstacles'][number];

    render(
      <GardenCanvas
        garden={{ ...garden(), beds: [], obstacles: [ground] }}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        onSelectObstacle={onSelectObstacle}
        onAskWhatItIs={vi.fn()}
        size={SIZE}
        tool={null}
      />,
    );

    const shape = document.querySelector('[data-element-id="3"]')!;
    expect(shape.getAttribute('role')).toBeNull();
    expect(shape.getAttribute('tabindex')).toBeNull();

    fireEvent.click(shape);
    expect(onSelectObstacle).not.toHaveBeenCalled();
  });
});
