import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { SuggestionFilters } from '../api/client';
import { FilterBar } from './FilterBar';

const COUNTS = {
  height: { matched: 1188, unknown: 1044, excluded: 2152 },
};

function setup(filters: SuggestionFilters = {}, counts = {}) {
  const onChange = vi.fn();
  render(<FilterBar filters={filters} counts={counts} onChange={onChange} />);
  return onChange;
}

describe('FilterBar', () => {
  it('says nothing is filtered when nothing is', () => {
    setup();
    expect(screen.getByText(/Keine Filter aktiv/)).toBeDefined();
  });

  it('shows each active filter as its own removable chip', () => {
    // "Every active filter is visible and removable" — a filter the user cannot
    // see is a filter they cannot distrust.
    const onChange = setup({ heightMax: 0.5, colour: 'yellow' });
    expect(screen.getByText(/höchstens 0,5 m/)).toBeDefined();
    expect(screen.getByText(/gelb/)).toBeDefined();

    fireEvent.click(screen.getByRole('button', { name: 'Filter „höchstens 0,5 m“ entfernen' }));
    expect(onChange).toHaveBeenCalledWith({ colour: 'yellow' });
  });

  it('reports how many species the filter could not judge', () => {
    // The number is the whole point: height is recorded for 44% of the
    // catalogue, and a filter that hides that looks identical to a broken one.
    setup({ heightMax: 0.5 }, COUNTS);
    expect(screen.getByText(/1\.044 Arten ohne Angabe/)).toBeDefined();
  });

  it('offers to include the unjudged species, and says it is a choice', () => {
    const onChange = setup({ heightMax: 0.5 }, COUNTS);
    fireEvent.click(screen.getByRole('checkbox', { name: /ohne Angabe mitzeigen/ }));
    expect(onChange).toHaveBeenCalledWith({ heightMax: 0.5, includeUnknown: true });
  });

  it('does not offer the unknown toggle when nothing is unknown', () => {
    setup({ heightMax: 0.5 }, { height: { matched: 10, unknown: 0, excluded: 3 } });
    expect(screen.queryByRole('checkbox', { name: /ohne Angabe/ })).toBeNull();
  });

  it('warns that colour is recorded for a fraction of the catalogue', () => {
    // A filter over a 6.6%-covered trait must not look like one over a
    // 100%-covered trait.
    setup({ colour: 'yellow' }, { colour: { matched: 108, unknown: 3860, excluded: 0 } });
    expect(screen.getByText(/Farbe ist nur für wenige Arten erfasst/)).toBeDefined();
  });

  it('clears everything at once', () => {
    const onChange = setup({ heightMax: 0.5, colour: 'yellow', floweringMonth: 6 });
    fireEvent.click(screen.getByRole('button', { name: 'Alle Filter entfernen' }));
    expect(onChange).toHaveBeenCalledWith({});
  });

  it('names the month rather than showing its number', () => {
    setup({ floweringMonth: 6 });
    expect(screen.getByText(/blüht im Juni/)).toBeDefined();
  });
});
