import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { GardenCanvas } from './GardenCanvas';

function bed(overrides: Partial<GardenOut['beds'][number]> = {}): GardenOut['beds'][number] {
  return {
    bed_id: 1,
    // Wave 15: a bed carries the same geometry an obstacle does.
    kind: 'bed',
    shape: 'polygon',
    x: 0,
    y: 0,
    points: null,
    width: null,
    constraint_hint: null,
    name: 'Südbeet',
    polygon: [[0, 0], [3, 0], [3, 2], [0, 2]],
    soil_type: 'loam',
    moisture: 'fresh',
    ellenberg_l: 8,
    ellenberg_m: 5,
    ellenberg_n: 5.5,
    ellenberg_r: 6.5,
    sun_hours: 6.4,
    slope_deg: null,
    aspect_deg: null,
    light_computed_at: '2026-08-28T10:00:00+00:00',
    height_above_ground: 0,
    label: null,
    plantings: [],
    ...overrides,
  };
}

function garden(overrides: Partial<GardenOut> = {}): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {},
    share_token: 'tok',
    name: 'Testgarten',
    latitude: 52.5,
    longitude: 13.4,
    created_at: '',
    updated_at: '',
    beds: [bed()],
    obstacles: [],
    ...overrides,
  };
}

/**
 * Drawing (Wave 7).
 *
 * jsdom gives every element a zero-sized bounding rect, so a pointer position
 * would convert to NaN metres. The canvas is therefore told its size rather
 * than measuring it — which it needs anyway, since an SVG that has not been
 * laid out yet measures zero in a real browser too.
 */
describe('GardenCanvas — drawing', () => {
  function draw(props: Partial<Parameters<typeof GardenCanvas>[0]> = {}) {
    const onDrawBed = vi.fn();
    render(
      <GardenCanvas
        garden={garden()}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={{ widthPx: 800, heightPx: 600 }}
        onDrawBed={onDrawBed}
        tool="polygon"
        {...props}
      />,
    );
    return onDrawBed;
  }

  function surface(): SVGSVGElement {
    return screen.getByTestId('canvas-surface') as unknown as SVGSVGElement;
  }

  function clickAt(x: number, y: number): void {
    fireEvent.click(surface(), { clientX: x, clientY: y });
  }

  it('states the grid spacing in words', () => {
    // A grid that silently stops being one metre is a measurement that is wrong.
    draw();
    expect(screen.getByText(/Raster 1 m/)).toBeDefined();
  });

  it('zooms out with a button, and says so', () => {
    draw();
    fireEvent.click(screen.getByRole('button', { name: 'Herauszoomen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Herauszoomen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Herauszoomen' }));
    expect(screen.getByText(/Raster (5|25|100) m/)).toBeDefined();
  });

  it('offers zoom as buttons, not only as a wheel gesture', () => {
    // A wheel-only zoom locks out anyone without one, and anyone whose hands do
    // not do precise scrolls.
    draw();
    expect(screen.getByRole('button', { name: 'Hineinzoomen' })).toBeDefined();
    expect(screen.getByRole('button', { name: 'Herauszoomen' })).toBeDefined();
  });

  it('does not accept clicks as vertices until a tool is armed', () => {
    // The polygon tool *is* the drawing mode since Wave 11 dropped the separate
    // "Beet zeichnen" button — a shape is drawn and named afterwards.
    const onDrawBed = vi.fn();
    render(
      <GardenCanvas
        garden={garden()} selectedBedId={null} onSelectBed={vi.fn()}
        size={{ widthPx: 800, heightPx: 600 }} onDrawBed={onDrawBed} tool={null}
      />,
    );
    fireEvent.click(screen.getAllByTestId('canvas-surface')[0]!, {
      clientX: 400, clientY: 300,
    });
    expect(screen.queryByTestId('draft')).toBeNull();
    expect(onDrawBed).not.toHaveBeenCalled();
  });

  it('collects vertices once drawing is started', () => {
    draw();
    clickAt(400, 300);
    clickAt(500, 300);
    expect(screen.getByTestId('draft')).toBeDefined();
    expect(screen.getByText(/2 Punkte/)).toBeDefined();
  });

  it('hands back garden metres, snapped to the grid', () => {
    // 800 px across 40 m at centre (0,0): 20 px per metre, centre at (400, 300).
    const onDrawBed = draw();
    clickAt(400, 300);
    clickAt(480, 300);
    clickAt(480, 220);
    fireEvent.click(screen.getByRole('button', { name: 'Fertig' }));
    expect(onDrawBed).toHaveBeenCalledWith([[0, 0], [4, 0], [4, 4]]);
  });

  it('refuses a shape with no inside, and says why', () => {
    // Two clicks and a double-click is a line. Stored, it would reach the area
    // and shading code as a shape with a centroid and no extent.
    const onDrawBed = draw();
    clickAt(400, 300);
    clickAt(480, 300);
    fireEvent.click(screen.getByRole('button', { name: 'Fertig' }));
    expect(onDrawBed).not.toHaveBeenCalled();
    expect(screen.getByText(/mindestens drei/i)).toBeDefined();
  });

  it('refuses an outline that crosses itself', () => {
    const onDrawBed = draw();
    clickAt(400, 300);
    clickAt(480, 220);
    clickAt(480, 300);
    clickAt(400, 220);
    fireEvent.click(screen.getByRole('button', { name: 'Fertig' }));
    expect(onDrawBed).not.toHaveBeenCalled();
    expect(screen.getByText(/überschneidet/i)).toBeDefined();
  });

  it('undoes the last vertex', () => {
    draw();
    clickAt(400, 300);
    clickAt(480, 300);
    fireEvent.click(screen.getByRole('button', { name: 'Rückgängig' }));
    expect(screen.getByText(/1 Punkt\b/)).toBeDefined();
  });

  it('redoes what it undid', () => {
    draw();
    clickAt(400, 300);
    clickAt(480, 300);
    fireEvent.click(screen.getByRole('button', { name: 'Rückgängig' }));
    fireEvent.click(screen.getByRole('button', { name: 'Wiederherstellen' }));
    expect(screen.getByText(/2 Punkte/)).toBeDefined();
  });

  it('abandons the draft on Escape', () => {
    draw();
    clickAt(400, 300);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByTestId('draft')).toBeNull();
  });

  it('places freely while Alt is held', () => {
    // A hedge does not run along grid lines just because the tool drew some.
    const onDrawBed = draw();
    fireEvent.click(surface(), { clientX: 410, clientY: 300, altKey: true });
    fireEvent.click(surface(), { clientX: 480, clientY: 300 });
    fireEvent.click(surface(), { clientX: 480, clientY: 220 });
    fireEvent.click(screen.getByRole('button', { name: 'Fertig' }));
    const polygon = onDrawBed.mock.calls[0]?.[0] as number[][];
    expect(polygon[0]?.[0]).toBeCloseTo(0.5, 6);
  });

  it('keeps the existing beds operable while no tool is armed', () => {
    // With a tool armed they are deliberately not: the click belongs to the
    // drawing. That case is GardenCanvas.focus.test.tsx.
    render(
      <GardenCanvas
        garden={garden()} selectedBedId={null} onSelectBed={vi.fn()}
        size={{ widthPx: 800, heightPx: 600 }} onDrawBed={vi.fn()}
      />,
    );
    expect(screen.getAllByRole('button', { name: /Südbeet/ })[0]).toBeDefined();
  });
});

describe('GardenCanvas — panning', () => {
  it('drags the view without the garden moving under the pointer', () => {
    // Zoom without pan strands a user the moment they zoom in: the rest of
    // their garden is off screen with no way to reach it. No tool armed — a
    // drag is a pan only when it is not a drawing gesture.
    render(
      <GardenCanvas
        garden={garden()}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={{ widthPx: 800, heightPx: 600 }}
        onDrawBed={vi.fn()}
      />,
    );
    const svg = screen.getByTestId('canvas-surface');
    const before = svg.getAttribute('viewBox');
    fireEvent.pointerDown(svg, { clientX: 400, clientY: 300 });
    fireEvent.pointerMove(svg, { clientX: 500, clientY: 300 });
    fireEvent.pointerUp(svg);
    expect(svg.getAttribute('viewBox')).not.toBe(before);
  });

  it('does not pan while drawing — a drag there is a misplaced vertex', () => {
    render(
      <GardenCanvas
        garden={garden()}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={{ widthPx: 800, heightPx: 600 }}
        onDrawBed={vi.fn()}
        tool="polygon"
      />,
    );
    const svg = screen.getByTestId('canvas-surface');
    const before = svg.getAttribute('viewBox');
    fireEvent.pointerDown(svg, { clientX: 400, clientY: 300 });
    fireEvent.pointerMove(svg, { clientX: 500, clientY: 300 });
    expect(svg.getAttribute('viewBox')).toBe(before);
  });
});

describe('GardenCanvas — the wheel does not steal the page', () => {
  function mounted() {
    render(
      <GardenCanvas
        garden={garden()}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={{ widthPx: 800, heightPx: 600 }}
        onDrawBed={vi.fn()}
      />,
    );
    return screen.getByTestId('canvas-surface');
  }

  // fireEvent rather than dispatchEvent: a state update from a listener added
  // outside React is not flushed before the next line, so the DOM would still
  // show the old viewBox and the test would pass for the wrong reason.
  // fireEvent's return value is false when the handler called preventDefault.

  it('lets a plain scroll through instead of zooming', () => {
    // Found by loading the page: the pointer sat over the canvas, the page
    // scrolled, and every tick was swallowed as a zoom step until the view hit
    // its 1000 m limit. A plan you cannot scroll past is not a plan you can use.
    const svg = mounted();
    const before = svg.getAttribute('viewBox');
    const notCancelled = fireEvent.wheel(svg, { deltaY: 120 });
    expect(svg.getAttribute('viewBox')).toBe(before);
    expect(notCancelled).toBe(true);
  });

  it('zooms when Ctrl is held, and takes the event', () => {
    const svg = mounted();
    const before = svg.getAttribute('viewBox');
    const notCancelled = fireEvent.wheel(svg, { deltaY: 120, ctrlKey: true });
    expect(svg.getAttribute('viewBox')).not.toBe(before);
    expect(notCancelled).toBe(false);
  });

  it('zooms on Cmd too, for the Mac gesture', () => {
    const svg = mounted();
    const before = svg.getAttribute('viewBox');
    fireEvent.wheel(svg, { deltaY: -120, metaKey: true });
    expect(svg.getAttribute('viewBox')).not.toBe(before);
  });
});
