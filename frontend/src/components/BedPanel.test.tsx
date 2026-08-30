import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { KINDS } from '../kinds';
import { BedPanel } from './BedPanel';

function garden(bedOverrides: Partial<GardenOut['beds'][number]> = {}): GardenOut {
  return {
    unidentified_plantings: 0,
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
        { planting_id: 1, taxon_id: 7, canonical_name: 'Salvia pratensis', raw_name: null, quantity: 3, added_at: '' },
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
        { planting_id: 1, taxon_id: 7, canonical_name: 'Salvia pratensis', raw_name: null, quantity: 3, added_at: '' },
        { planting_id: 2, taxon_id: 8, canonical_name: 'Salix caprea', raw_name: null, quantity: 1, added_at: '' },
      ],
    });
    render(<BedPanel garden={g} selectedBedId={null} {...noop} />);
    expect(screen.getByRole('button', { name: /2 Arten gepflanzt/ })).toBeDefined();
  });
});

describe('BedPanel — adding an obstacle by hand', () => {
  function panel() {
    const onAddObstacle = vi.fn().mockResolvedValue(undefined);
    render(
      <BedPanel
        garden={garden()}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        onAddBed={vi.fn()}
        onAddObstacle={onAddObstacle}
        busy={false}
      />,
    );
    // Scoped: the bed form above has its own Breite and Tiefe.
    const form = within(screen.getByRole('form', { name: 'Hindernis hinzufügen' }));
    return { onAddObstacle, form };
  }

  it('offers the kinds rather than asking the user to spell one', () => {
    // This was a free text field. Anything not in the server's closed set came
    // back a 422 the user had no way to predict.
    const { form } = panel();
    const select = form.getByLabelText('Art') as HTMLSelectElement;
    expect([...select.options].map((o) => o.value)).toEqual(KINDS.map((k) => k.kind));
  });

  it('fills in the size and height that come with a kind', () => {
    const { form } = panel();
    fireEvent.change(form.getByLabelText('Art'), { target: { value: 'house' } });
    expect((form.getByLabelText('Breite') as HTMLInputElement).value).toBe('10');
    expect((form.getByLabelText('Tiefe') as HTMLInputElement).value).toBe('8');
    expect((form.getByLabelText('Höhe') as HTMLInputElement).value).toBe('6');
  });

  it('sends no height for a surface', () => {
    // Paving has none, and inventing one would have it shade the bed next door.
    const { onAddObstacle, form } = panel();
    fireEvent.change(form.getByLabelText('Art'), { target: { value: 'paving' } });
    fireEvent.click(form.getByRole('button', { name: 'Hindernis hinzufügen' }));
    expect(onAddObstacle).toHaveBeenCalledWith(
      expect.objectContaining({ kind: 'paving', width: 4, depth: 3 }),
    );
    expect(onAddObstacle.mock.calls[0]?.[0]).not.toHaveProperty('height');
  });

  it('sends width and depth, not a doubled radius', () => {
    const { onAddObstacle, form } = panel();
    fireEvent.change(form.getByLabelText('Art'), { target: { value: 'hedge' } });
    fireEvent.click(form.getByRole('button', { name: 'Hindernis hinzufügen' }));
    expect(onAddObstacle).toHaveBeenCalledWith(
      expect.objectContaining({ kind: 'hedge', width: 6, depth: 0.6, height: 2 }),
    );
  });
});
