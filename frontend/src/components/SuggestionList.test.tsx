import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { BedSuggestions } from '../api/client';
import { SuggestionList } from './SuggestionList';

function item(overrides: Partial<BedSuggestions['items'][number]> = {}) {
  return {
    taxon_id: 1,
    canonical_name: 'Sambucus nigra',
    family: 'Adoxaceae',
    height_max_m: 6,
    flowering_start_month: 6,
    flowering_end_month: 7,
    flower_colour: 'white',
    colour_known: true,
    bird_partners: 100,
    space_m2: 28.3,
    fits_bed: true,
    fit: { score: 0.9, axes: {} },
    ...overrides,
  } as BedSuggestions['items'][number];
}

function suggestions(overrides: Partial<BedSuggestions> = {}): BedSuggestions {
  return {
    bed_id: 1,
    bed_name: 'Hecke',
    site_axes: { ellenberg_l: 6 },
    total: 1,
    items: [item()],
    woody: [],
    woody_total: 0,
    filters: {},
    ...overrides,
  } as BedSuggestions;
}

function show(props: Partial<Parameters<typeof SuggestionList>[0]> = {}) {
  render(
    <SuggestionList
      suggestions={suggestions()}
      includeTrees={false}
      onPlant={vi.fn()}
      onShowInfo={vi.fn()}
      busy={false}
      {...props}
    />,
  );
}

describe('SuggestionList', () => {
  it('does not claim woody plants are hidden when they are in the list', () => {
    // The sentence was hardcoded and went on asserting it after the user had
    // switched woody plants on — visible in the running app, invisible to tests.
    show({ includeTrees: true });
    expect(screen.getByText(/eigenen Liste/)).toBeDefined();
    expect(screen.queryByText(/ausgeblendet/)).toBeNull();
  });

  it('gives woody plants their own list rather than burying them', () => {
    // Ranked into one list they sorted below ~2,000 perennials — the same
    // invisibility as excluding them, with a better argument.
    show({
      suggestions: suggestions({
        woody: [item({ taxon_id: 9, canonical_name: 'Salix caprea', fits_bed: false, space_m2: 50 })],
        woody_total: 1,
      }),
    });
    expect(screen.getByRole('heading', { name: /Gehölze für diesen Standort/ })).toBeDefined();
    expect(screen.getByText('Salix caprea')).toBeDefined();
  });

  it('says nothing about woody plants when there are none to show', () => {
    show();
    expect(screen.queryByRole('heading', { name: /Gehölze/ })).toBeNull();
  });

  it('prices a plant too large for the bed instead of hiding it', () => {
    // Wave 4 hid every woody plant from every bed, and with them the best
    // forage plants in the catalogue. Showing what an oak would take is more
    // use than pretending the catalogue does not contain one.
    show({
      suggestions: suggestions({
        items: [],
        woody: [item({ canonical_name: 'Quercus robur', space_m2: 201.1, fits_bed: false })],
        woody_total: 1,
      }),
    });
    expect(screen.getByText('Quercus robur')).toBeDefined();
    expect(screen.getByText(/braucht ~201 m²/)).toBeDefined();
  });

  it('says nothing about room for a plant that fits', () => {
    show();
    expect(screen.queryByText(/braucht ~/)).toBeNull();
  });

  it('says woody plants are hidden when they are', () => {
    show();
    expect(screen.getByText(/ausgeblendet/)).toBeDefined();
  });

  it('names what the bird number counts, once, not per row', () => {
    // "100 Vogelarten" beside a plant reads as a value score. It is a record of
    // being eaten, and 99.7% of the bird relations in GloBI are exactly that.
    show();
    expect(screen.getByText(/100 Vogelarten als Nahrung/)).toBeDefined();
    expect(screen.getByText(/meist Früchte oder Samen/)).toBeDefined();
  });

  it('stays silent about birds when none are recorded', () => {
    show({ suggestions: suggestions({ items: [item({ bird_partners: null })] }) });
    expect(screen.queryByText(/Vogelart/)).toBeNull();
    expect(screen.queryByText(/als Nahrung/)).toBeNull();
  });

  it('does not print a zero for a plant no bird was recorded on', () => {
    show({ suggestions: suggestions({ items: [item({ bird_partners: 0 })] }) });
    expect(screen.queryByText(/0 Vogelarten/)).toBeNull();
  });

  it('names the colour in German, as the pickers do', () => {
    // The list printed the catalogue value raw, so a species recorded as
    // `brown` read "brown" next to a colour picker offering "braun".
    show({ suggestions: suggestions({ items: [item({ flower_colour: 'brown' })] }) });

    expect(screen.getByText('braun')).toBeDefined();
    expect(screen.queryByText('brown')).toBeNull();
  });

  it('shows a colour it has no German name for rather than nothing', () => {
    show({ suggestions: suggestions({ items: [item({ flower_colour: 'cream' })] }) });

    expect(screen.getByText('cream')).toBeDefined();
  });
});
