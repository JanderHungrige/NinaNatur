import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { ImprovementsOut, ScoreOut } from '../api/client';
import { InsectScore } from './InsectScore';

function score(overrides: Partial<ScoreOut> = {}): ScoreOut {
  return {
    score: 42,
    by_month: { '6': 12, '7': 25 },
    by_species: [
      {
        taxon_id: 1, canonical_name: 'Achillea millefolium',
        german_partners: 959, origin: 'native', forage: 31, months: [7, 8],
      },
    ],
    by_group: { bee: 170, butterfly: 203, hoverfly: 0 },
    plantings_total: 1,
    plantings_without_interaction_data: 0,
    is_empty: false,
    ...overrides,
  };
}

function improvements(overrides: Partial<ImprovementsOut> = {}): ImprovementsOut {
  return {
    current_score: 42,
    additions: [
      {
        taxon_id: 2, canonical_name: 'Bellis perennis', bed_id: 1, bed_name: 'Beet',
        gain: 34, resulting_score: 76, reason: 'schließt die Lücke im April und Mai',
        german_partners: 200, replaces_planting_id: null, replaces_name: null,
      },
    ],
    swaps: [
      {
        taxon_id: 2, canonical_name: 'Bellis perennis', bed_id: 1, bed_name: 'Beet',
        gain: 30, resulting_score: 72, reason: 'schließt die Lücke im April',
        german_partners: 200, replaces_planting_id: 7, replaces_name: 'Achillea millefolium',
      },
    ],
    ...overrides,
  };
}

const noop = { onApply: vi.fn(async () => undefined), busy: false };

describe('InsectScore', () => {
  it('shows the number with its scale, not bare', () => {
    render(<InsectScore score={score()} improvements={null} {...noop} />);
    expect(screen.getByText('42')).toBeDefined();
    expect(screen.getByText(/von 100/)).toBeDefined();
  });

  it('breaks the number down by insect group', () => {
    // "1,055 partners" is not something a gardener can act on.
    render(<InsectScore score={score()} improvements={null} {...noop} />);
    expect(screen.getByText('170 Wildbienenarten')).toBeDefined();
    expect(screen.getByText('203 Schmetterlingsarten')).toBeDefined();
  });

  it('uses the singular for exactly one', () => {
    // "1 Schwebfliegenarten" is the same bug as "1 Beete".
    const s = score({ by_group: { bee: 1, hoverfly: 3 } });
    render(<InsectScore score={s} improvements={null} {...noop} />);
    expect(screen.getByText('1 Wildbienenart')).toBeDefined();
    expect(screen.getByText('3 Schwebfliegenarten')).toBeDefined();
  });

  it('omits groups with no records rather than showing a zero', () => {
    render(<InsectScore score={score()} improvements={null} {...noop} />);
    expect(screen.queryByText(/Schwebfliegenarten/)).toBeNull();
  });

  it('lists every contributing species so the score can be interrogated', () => {
    render(<InsectScore score={score()} improvements={null} {...noop} />);
    expect(screen.getByRole('rowheader', { name: 'Achillea millefolium' })).toBeDefined();
    expect(screen.getByText('959')).toBeDefined();
    expect(screen.getByText('heimisch')).toBeDefined();
  });

  it('says when a species has no partner records instead of showing zero', () => {
    const s = score({
      by_species: [{
        taxon_id: 1, canonical_name: 'Unerforscht', german_partners: null,
        origin: 'unknown', forage: 1, months: [6],
      }],
    });
    render(<InsectScore score={s} improvements={null} {...noop} />);
    expect(screen.getByText('nicht erfasst')).toBeDefined();
  });

  it('teaches instead of showing a zero for an empty garden', () => {
    const s = score({ is_empty: true, plantings_total: 0, score: 0 });
    render(<InsectScore score={s} improvements={null} {...noop} />);
    expect(screen.getByText(/Noch nichts gepflanzt/)).toBeDefined();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('offers additions with their reason and resulting score', () => {
    render(<InsectScore score={score()} improvements={improvements()} {...noop} />);
    expect(screen.getByText(/schließt die Lücke im April und Mai/)).toBeDefined();
    expect(screen.getByText(/\+34 → 76/)).toBeDefined();
  });

  it('keeps swaps behind a disclosure, because they remove something', () => {
    // The score will recommend removing a valuable plant whose month is full.
    render(<InsectScore score={score()} improvements={improvements()} {...noop} />);
    const summary = screen.getByText(/Wenn das Beet voll ist/);
    expect(summary.closest('details')?.hasAttribute('open')).toBe(false);
  });

  it('warns that a swap can remove a well-connected plant', () => {
    render(<InsectScore score={score()} improvements={improvements()} {...noop} />);
    expect(screen.getByText(/ihr Monat ist dann schlicht schon gedeckt/)).toBeDefined();
  });

  it('reports plantings that had no interaction data', () => {
    const s = score({ plantings_without_interaction_data: 2 });
    render(<InsectScore score={s} improvements={null} {...noop} />);
    expect(screen.getByText(/unbekannt ist nicht\s+wertlos/)).toBeDefined();
  });
});
