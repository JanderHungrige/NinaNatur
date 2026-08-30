import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Sightlines } from './Sightlines';

const ROWS = [
  { planting_id: 1, name: 'Bodendecker', bed_id: 1, height_m: 0.2,
    visible: false, visible_from_m: 2.6, hidden_by: 7, estimated: false },
  { planting_id: 2, name: 'Hochstaude', bed_id: 1, height_m: 3.0,
    visible: true, visible_from_m: 0, hidden_by: null, estimated: false },
  { planting_id: 3, name: 'Namenlos', bed_id: 1, height_m: null,
    visible: null, visible_from_m: null, hidden_by: null, estimated: false },
];

function show(overrides: Partial<Parameters<typeof Sightlines>[0]> = {}) {
  render(
    <Sightlines
      result={{ plantings: ROWS, estimated_count: 0 }}
      onClear={vi.fn()}
      {...overrides}
    />,
  );
}

describe('Sightlines', () => {
  it('says what is hidden and what is not', () => {
    show();
    expect(screen.getByText(/Bodendecker/)).toBeDefined();
    expect(screen.getByText(/verdeckt/i)).toBeDefined();
  });

  it('says from which height something would be visible', () => {
    // More useful than a yes or no: it says which plants belong there.
    show();
    expect(screen.getByText(/ab 2,6 m/)).toBeDefined();
  });

  it('does not guess for a plant with no recorded height', () => {
    // Height is recorded for 44% of the catalogue. A confident answer on top of
    // nothing is the failure this project keeps refusing.
    show();
    expect(screen.getByText(/Höhe nicht erfasst/)).toBeDefined();
  });

  it('says once when answers rest on estimated heights', () => {
    show({ result: { plantings: ROWS, estimated_count: 2 } });
    expect(screen.getByText(/geschätzten Höhen/)).toBeDefined();
  });

  it('says nothing about estimates when there are none', () => {
    show();
    expect(screen.queryByText(/geschätzten Höhen/)).toBeNull();
  });

  it('uses the singular for one estimate', () => {
    show({ result: { plantings: ROWS, estimated_count: 1 } });
    expect(screen.getByText(/1 Antwort/)).toBeDefined();
  });
});
