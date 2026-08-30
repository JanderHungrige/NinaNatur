import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { GardenCanvas } from './GardenCanvas';

function bed(overrides: Partial<GardenOut['beds'][number]> = {}): GardenOut['beds'][number] {
  return {
    bed_id: 1,
    name: 'Südbeet',
    polygon: [[0, 0], [3, 0], [3, 2], [0, 2]],
    soil_type: 'loam',
    moisture: 'fresh',
    ellenberg_l: 8,
    ellenberg_m: 5,
    ellenberg_n: 5.5,
    ellenberg_r: 6.5,
    sun_hours: 6.4,
    light_computed_at: '2026-08-28T10:00:00+00:00',
    height_above_ground: 0,
    label: null,
    plantings: [],
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
      obstacles: [{ obstacle_id: 1, kind: 'wall', label: null, height_source: 'user',
          x: 0, y: -4, radius: 5, height: 6 }],
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
