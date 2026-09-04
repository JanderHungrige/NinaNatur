import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { BedPanel } from './BedPanel';

function garden(bedOverrides: Partial<GardenOut['beds'][number]> = {}): GardenOut {
  return {
    unidentified_plantings: 0,
    soil_type: null,
    moisture: null,
    observed_colours: {},
    share_token: 'tok',
    name: 'Testgarten',
    latitude: 52.5,
    longitude: 13.4,
    created_at: '',
    updated_at: '',
    obstacles: [],
    beds: [
      {
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
        polygon: [],
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
        ...bedOverrides,
      },
    ],
  };
}

const noop = {
  onSelectBed: vi.fn(),
  onAddBed: vi.fn(async () => undefined),
  onAddObstacle: vi.fn(async () => undefined),
  busy: false,
};

describe('BedPanel', () => {
  it('spells out the bed button name instead of letting spans run together', () => {
    // Adjacent spans concatenate with no space: a screen reader would otherwise
    // say "Südbeetnoch nicht berechnet".
    render(<BedPanel garden={garden()} selectedBedId={null} {...noop} />);
    const button = screen.getByRole('button', { name: /^Beet Südbeet, 6\.4 h\/Tag/ });
    expect(button.getAttribute('aria-label')).toContain('nichts gepflanzt');
  });

  it('says a bed has no computed light rather than showing zero', () => {
    render(
      <BedPanel
        garden={garden({ sun_hours: null, ellenberg_l: null })}
        selectedBedId={null}
        {...noop}
      />,
    );
    expect(screen.getByRole('button', { name: /noch nicht berechnet/ })).toBeDefined();
  });

  it('reports how many species are planted', () => {
    const g = garden({
      plantings: [
        { planting_id: 1, taxon_id: 7, canonical_name: 'Salvia pratensis', raw_name: null, quantity: 3, added_at: '', x: null, y: null },
      ],
    });
    render(<BedPanel garden={g} selectedBedId={null} {...noop} />);
    // Singular, not "1 Art(en)". The label is read aloud by a screen reader,
    // and the parenthetical dodge is the same bug as "1 Beete" wearing a hat.
    expect(screen.getByRole('button', { name: /1 Art gepflanzt/ })).toBeDefined();
  });

  it('uses the plural for more than one species', () => {
    const g = garden({
      plantings: [
        { planting_id: 1, taxon_id: 7, canonical_name: 'Salvia pratensis', raw_name: null, quantity: 3, added_at: '', x: null, y: null },
        { planting_id: 2, taxon_id: 8, canonical_name: 'Salix caprea', raw_name: null, quantity: 1, added_at: '', x: null, y: null },
      ],
    });
    render(<BedPanel garden={g} selectedBedId={null} {...noop} />);
    expect(screen.getByRole('button', { name: /2 Arten gepflanzt/ })).toBeDefined();
  });
});

// The tests for "Beet hinzufügen" and "Hindernis hinzufügen" stood here. Both
// forms predate drawing: they were the only way to put anything on a plan
// before Wave 11, and by Wave 12 they were the slower way to do what a drag
// does — asking for coordinates the user would have to work out from the
// drawing in front of them.

describe('BedPanel — after the forms went', () => {
  it('still lets a bed be picked, which is what the panel is for', () => {
    const onSelectBed = vi.fn();
    render(
      <BedPanel garden={garden()} selectedBedId={null} onSelectBed={onSelectBed} />,
    );
    fireEvent.click(screen.getByRole('button', { name: /Südbeet/ }));
    expect(onSelectBed).toHaveBeenCalled();
  });

  it('offers no way to type a bed into existence', () => {
    // Drawing is the way. A second, slower path that asks for coordinates the
    // user would have to read off the plan is worse than none.
    render(<BedPanel garden={garden()} selectedBedId={null} onSelectBed={vi.fn()} />);
    expect(screen.queryByText('Beet hinzufügen')).toBeNull();
    expect(screen.queryByText('Hindernis hinzufügen')).toBeNull();
  });
});
