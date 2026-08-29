import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { BedPanel } from './BedPanel';

function garden(bedOverrides: Partial<GardenOut['beds'][number]> = {}): GardenOut {
  return {
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
        { planting_id: 1, taxon_id: 7, canonical_name: 'Salvia pratensis', quantity: 3, added_at: '' },
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
        { planting_id: 1, taxon_id: 7, canonical_name: 'Salvia pratensis', quantity: 3, added_at: '' },
        { planting_id: 2, taxon_id: 8, canonical_name: 'Salix caprea', quantity: 1, added_at: '' },
      ],
    });
    render(<BedPanel garden={g} selectedBedId={null} {...noop} />);
    expect(screen.getByRole('button', { name: /2 Arten gepflanzt/ })).toBeDefined();
  });
});
