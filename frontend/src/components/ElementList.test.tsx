import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { ElementList } from './ElementList';

function obstacle(id: number, kind: string, label: string | null = null) {
  return {
    obstacle_id: id, kind, label, height_source: 'user', x: 0, y: 0,
    shape: 'polygon', width: null, constraint_hint: null, points: null,
    height: null,
    footprint: [[0, 0], [4, 0], [4, 3], [0, 3]],
  } as GardenOut['obstacles'][number];
}

function garden(obstacles: GardenOut['obstacles'] = [], beds: GardenOut['beds'] = []): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null,
    share_token: 'tok', name: 'G', latitude: 52.5, longitude: 13.4,
    created_at: '', updated_at: '', beds, obstacles,
  };
}

describe('ElementList', () => {
  it('lists everything drawn, beds included', () => {
    render(
      <ElementList
        garden={garden([obstacle(1, 'house')], [{
          bed_id: 9, name: 'Südbeet', polygon: [[0, 0], [2, 0], [2, 2], [0, 2]],
          soil_type: 'loam', moisture: 'fresh', ellenberg_l: null, ellenberg_m: null,
          ellenberg_n: null, ellenberg_r: null, sun_hours: null,
          light_computed_at: null, height_above_ground: 0, label: null, plantings: [],
        }])}
        selectedId={null}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', { name: /Wohnhaus/ })).toBeDefined();
    expect(screen.getByRole('button', { name: /Südbeet/ })).toBeDefined();
  });

  it('reaches an element that is buried under another', () => {
    // The whole reason the list exists: draw order helps with two shapes and
    // nothing helps with three.
    const onSelect = vi.fn();
    render(
      <ElementList
        garden={garden([obstacle(1, 'lawn'), obstacle(2, 'pond'), obstacle(3, 'shed')])}
        selectedId={null}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /Teich/ }));
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it('shows what each one covers, so two of a kind can be told apart', () => {
    render(
      <ElementList garden={garden([obstacle(1, 'bed'), obstacle(2, 'bed')])}
        selectedId={null} onSelect={vi.fn()} />,
    );
    expect(screen.getAllByRole('button', { name: /12,0 m²/ })).toHaveLength(2);
  });

  it('marks which one is selected', () => {
    render(
      <ElementList garden={garden([obstacle(1, 'house')])} selectedId={1} onSelect={vi.fn()} />,
    );
    expect(
      screen.getByRole('button', { name: /Wohnhaus/ }).getAttribute('aria-pressed'),
    ).toBe('true');
  });

  it('says so when nothing has been drawn', () => {
    render(<ElementList garden={garden()} selectedId={null} onSelect={vi.fn()} />);
    expect(screen.getByText(/Noch nichts gezeichnet/)).toBeDefined();
  });

  it('prefers the user’s own words over the kind', () => {
    render(
      <ElementList garden={garden([obstacle(1, 'tree', 'Die Buche vom Nachbarn')])}
        selectedId={null} onSelect={vi.fn()} />,
    );
    expect(screen.getByRole('button', { name: /Die Buche vom Nachbarn/ })).toBeDefined();
  });
});
