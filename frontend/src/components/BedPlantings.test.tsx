import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { BedPlantings } from './BedPlantings';

type Bed = GardenOut['beds'][number];

function planting(overrides: Partial<Bed['plantings'][number]> = {}) {
  return {
    planting_id: 1,
    taxon_id: 42,
    canonical_name: 'Salvia pratensis',
    raw_name: null,
    quantity: 3,
    added_at: '2026-09-01T10:00:00+00:00',
    ...overrides,
  } as Bed['plantings'][number];
}

function bed(plantings: Bed['plantings']): Bed {
  return {
    bed_id: 1, name: 'Staudenbeet', kind: 'bed', shape: 'polygon',
    x: 0, y: 0, points: null, width: null, constraint_hint: null,
    polygon: [[0, 0], [3, 0], [3, 2], [0, 2]],
    soil_type: null, moisture: null, ellenberg_l: null, ellenberg_m: null,
    ellenberg_n: null, ellenberg_r: null, sun_hours: null,
    light_computed_at: null, height_above_ground: 0, label: null, plantings,
  } as Bed;
}

function show(plantings: Bed['plantings'], props: Record<string, unknown> = {}) {
  const onRemove = vi.fn();
  const onShowInfo = vi.fn();
  render(
    <BedPlantings
      bed={bed(plantings)}
      onRemove={onRemove}
      onShowInfo={onShowInfo}
      busy={false}
      {...props}
    />,
  );
  return { onRemove, onShowInfo };
}

describe('BedPlantings', () => {
  it('names the bed and what stands in it', () => {
    show([planting(), planting({ planting_id: 2, canonical_name: 'Achillea millefolium' })]);

    expect(screen.getByRole('heading', { name: 'In Staudenbeet' })).toBeDefined();
    expect(screen.getByText('Salvia pratensis')).toBeDefined();
    expect(screen.getByText('Achillea millefolium')).toBeDefined();
  });

  it('shows how many of each', () => {
    show([planting({ quantity: 3 })]);
    expect(screen.getByText(/× 3/)).toBeDefined();
  });

  it('says when a bed is empty rather than showing an empty list', () => {
    show([]);
    expect(screen.getByText(/Noch nichts gepflanzt/)).toBeDefined();
    expect(screen.queryByRole('button', { name: 'Entfernen' })).toBeNull();
  });

  it('asks before removing', () => {
    // A planting is a decision somebody made, sometimes weeks ago, and this row
    // is one keystroke away from the row above it.
    const { onRemove } = show([planting()]);

    fireEvent.click(screen.getByRole('button', { name: 'Entfernen' }));
    expect(onRemove).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Wirklich entfernen' }));
    expect(onRemove).toHaveBeenCalledWith(1);
  });

  it('lets the question be taken back', () => {
    const { onRemove } = show([planting()]);
    fireEvent.click(screen.getByRole('button', { name: 'Entfernen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Doch nicht' }));

    expect(onRemove).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Entfernen' })).toBeDefined();
  });

  it('asks about one row at a time', () => {
    // Two open questions are two chances to answer the wrong one.
    show([planting(), planting({ planting_id: 2, canonical_name: 'Achillea millefolium' })]);
    const [first, second] = screen.getAllByRole('button', { name: 'Entfernen' });

    fireEvent.click(first!);
    fireEvent.click(second!);

    expect(screen.getAllByRole('button', { name: 'Wirklich entfernen' })).toHaveLength(1);
  });

  it('shows a plant the catalogue could not name, and says so', () => {
    // It stands in the bed but counts for nothing in the insect score. Hiding
    // it would be worse: the gardener typed it in and would look for it.
    show([planting({ taxon_id: null, canonical_name: null, raw_name: 'Omas Rose' })]);

    expect(screen.getByText('Omas Rose')).toBeDefined();
    expect(screen.getByText(/nicht im Katalog/)).toBeDefined();
    expect(screen.queryByRole('button', { name: 'Info' })).toBeNull();
  });

  it('opens the same info panel the suggestions open', () => {
    const { onShowInfo } = show([planting()]);
    fireEvent.click(screen.getByRole('button', { name: 'Info' }));
    expect(onShowInfo).toHaveBeenCalledWith(42, 'Salvia pratensis');
  });
});
