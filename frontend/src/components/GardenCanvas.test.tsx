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

describe('GardenCanvas', () => {
  it('gives every bed an accessible name carrying its light', () => {
    render(<GardenCanvas garden={garden()} selectedBedId={null} onSelectBed={vi.fn()} />);
    expect(
      screen.getByRole('button', { name: /Südbeet.*6\.4 Sonnenstunden/ }),
    ).toBeDefined();
  });

  it('says light is not computed rather than showing zero hours', () => {
    // Unknown must never render as 0 — the same rule as every layer beneath.
    const g = garden({ beds: [bed({ sun_hours: null, ellenberg_l: null })] });
    render(<GardenCanvas garden={g} selectedBedId={null} onSelectBed={vi.fn()} />);
    expect(screen.getByRole('button', { name: /noch nicht berechnet/ })).toBeDefined();
    expect(screen.queryByRole('button', { name: /0\.0 Sonnenstunden/ })).toBeNull();
  });

  it('beds are reachable and operable by keyboard', () => {
    const onSelect = vi.fn();
    render(<GardenCanvas garden={garden()} selectedBedId={null} onSelectBed={onSelect} />);
    const shape = screen.getByRole('button', { name: /Südbeet/ });
    expect(shape.getAttribute('tabindex')).toBe('0');
    shape.focus();
    expect(document.activeElement).toBe(shape);
  });

  it('marks the selected bed with aria-pressed, not colour alone', () => {
    render(<GardenCanvas garden={garden()} selectedBedId={1} onSelectBed={vi.fn()} />);
    expect(screen.getByRole('button', { name: /Südbeet/ }).getAttribute('aria-pressed')).toBe('true');
  });

  it('names the plan itself so its contents are knowable without seeing it', () => {
    const g = garden({
      obstacles: [{ obstacle_id: 1, kind: 'wall', label: null, roof: 'unknown', eaves_m: null, height_source: 'user',
          x: 0, y: -4, shape: 'polygon', width: null, constraint_hint: 'rect',
          points: [[-5, -0.5], [5, -0.5], [5, 0.5], [-5, 0.5]], height: 6,
          footprint: [[-5, -4.5], [5, -4.5], [5, -3.5], [-5, -3.5]] }],
    });
    render(<GardenCanvas garden={g} selectedBedId={null} onSelectBed={vi.fn()} />);
    expect(screen.getByRole('group', { name: /1 Beet, 1 Hindernis/ })).toBeDefined();
  });

  it('draws north up: a bed further north sits higher on screen', () => {
    // Garden y is north, SVG y grows downward — getting this backwards would
    // silently mirror every plan.
    const g = garden({
      beds: [
        bed({ bed_id: 1, name: 'Nord', polygon: [[0, 10], [1, 10], [1, 11], [0, 11]] }),
        bed({ bed_id: 2, name: 'Süd', polygon: [[0, -10], [1, -10], [1, -9], [0, -9]] }),
      ],
    });
    const { container } = render(
      <GardenCanvas garden={g} selectedBedId={null} onSelectBed={vi.fn()} />,
    );
    const polygons = container.querySelectorAll('polygon');
    const yOf = (el: Element) =>
      Number.parseFloat((el.getAttribute('points') ?? '0,0').split(',')[1] ?? '0');
    expect(yOf(polygons[0]!)).toBeLessThan(yOf(polygons[1]!));
  });
});

describe('GardenCanvas — what the sun map says under the pointer', () => {
  function sunMap(hours: (number | null)[], roof = hours.map(() => false)) {
    return {
      map: {
        cell_m: 1, min_x: -1, min_y: -1, cols: 2, rows: 2,
        hours,
        roof,
        max_hours: 9.2,
        computed_at: '2026-09-07T10:00:00+00:00',
        stale: false,
        morning: hours.map((h) => (h === null ? null : h / 2)),
        misplaced: [],
      },
      mode: 'hours' as const,
    };
  }

  function plan(hours: (number | null)[] | null, roof?: boolean[]) {
    render(
      <GardenCanvas
        garden={garden()}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={{ widthPx: 600, heightPx: 400 }}
        {...(hours === null ? {} : { sunMap: sunMap(hours, roof) })}
      />,
    );
    const surface = screen.getByTestId('canvas-surface');
    // jsdom lays nothing out, so the surface has to be told where it is. The
    // view starts centred on the garden's origin, which is inside this map.
    surface.getBoundingClientRect = () =>
      ({ left: 0, top: 0, width: 600, height: 400 }) as DOMRect;
    return surface;
  }

  it('says nothing until the pointer is over the plan', () => {
    plan([9.2, 9.2, 9.2, 9.2]);
    expect(screen.queryByTestId('sun-readout')).toBeNull();
  });

  it('reads out the hours and what they are called', () => {
    // A wash cannot be read to one decimal place, and "volle Sonne" is the word
    // on the plant label somebody is holding.
    const surface = plan([9.2, 9.2, 9.2, 9.2]);
    fireEvent.pointerMove(surface, { clientX: 300, clientY: 200 });
    expect(screen.getByTestId('sun-readout').textContent).toBe('9.2 h · volle Sonne');
  });

  it('says when the hours it is reading are a roof', () => {
    // A different question from the ground's, and nothing is planted on one. A
    // reader who took 11 h for the bed below would have it exactly backwards:
    // the ground there is under a house.
    const surface = plan([11.0, 11.0, 11.0, 11.0], [true, true, true, true]);
    fireEvent.pointerMove(surface, { clientX: 300, clientY: 200 });
    expect(screen.getByTestId('sun-readout').textContent).toBe('Dach · 11.0 h · volle Sonne');
  });

  it('goes away when the pointer leaves', () => {
    const surface = plan([9.2, 9.2, 9.2, 9.2]);
    fireEvent.pointerMove(surface, { clientX: 300, clientY: 200 });
    fireEvent.pointerLeave(surface);
    expect(screen.queryByTestId('sun-readout')).toBeNull();
  });

  it('is not there at all when no map is being shown', () => {
    const surface = plan(null);
    fireEvent.pointerMove(surface, { clientX: 300, clientY: 200 });
    expect(screen.queryByTestId('sun-readout')).toBeNull();
  });
});
