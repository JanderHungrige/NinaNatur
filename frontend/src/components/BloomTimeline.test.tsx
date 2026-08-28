import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { TimelineOut } from '../api/client';
import { BloomTimeline, describeGap } from './BloomTimeline';

function timeline(overrides: Partial<TimelineOut> = {}): TimelineOut {
  return {
    mode: 'forage',
    months: Array.from({ length: 12 }, (_, i) => ({
      month: i + 1,
      coverage: i === 6 ? 1 : 0,
      species: i === 6 ? ['Achillea millefolium'] : [],
    })),
    gaps: [{ months: [3, 4, 5], length: 3 }],
    plantings_total: 1,
    plantings_without_interaction_data: 0,
    is_empty: false,
    ...overrides,
  };
}

describe('describeGap', () => {
  it('names a run the way a person would say it', () => {
    expect(describeGap([3, 4, 5])).toBe('Mär bis Mai');
  });

  it('names a single month without a range', () => {
    expect(describeGap([10])).toBe('Okt');
  });
});

describe('BloomTimeline', () => {
  it('renders every month as a table row, not only as a bar', () => {
    // Nothing here may be knowable only by looking at a shape.
    render(<BloomTimeline timeline={timeline()} forage onToggleForage={vi.fn()} busy={false} />);
    expect(screen.getAllByRole('row')).toHaveLength(13); // header + 12 months
    expect(screen.getByRole('rowheader', { name: 'Jul' })).toBeDefined();
  });

  it('marks gaps in text, not by colour alone', () => {
    render(<BloomTimeline timeline={timeline()} forage onToggleForage={vi.fn()} busy={false} />);
    expect(screen.getAllByText('Lücke').length).toBe(3);
    expect(screen.getByText(/Trachtlücke: Mär bis Mai/)).toBeDefined();
  });

  it('calls the gap a bloom gap when weighting is off', () => {
    render(
      <BloomTimeline timeline={timeline()} forage={false} onToggleForage={vi.fn()} busy={false} />,
    );
    expect(screen.getByText(/Blühlücke: Mär bis Mai/)).toBeDefined();
  });

  it('the mode control is a real labelled checkbox', () => {
    const toggle = vi.fn();
    render(<BloomTimeline timeline={timeline()} forage onToggleForage={toggle} busy={false} />);
    const box = screen.getByRole('checkbox', { name: /Insektenwert/ });
    expect((box as HTMLInputElement).checked).toBe(true);
  });

  it('teaches instead of drawing twelve empty bars', () => {
    // A chart of nothing looks broken rather than empty.
    const empty = timeline({ is_empty: true, plantings_total: 0, gaps: [] });
    render(<BloomTimeline timeline={empty} forage onToggleForage={vi.fn()} busy={false} />);
    expect(screen.queryByRole('table')).toBeNull();
    expect(screen.getByText(/Noch nichts gepflanzt/)).toBeDefined();
  });

  it('labels coverage as a share of the best month', () => {
    // An unlabelled 0.44 invites the reader to invent a unit.
    render(<BloomTimeline timeline={timeline()} forage onToggleForage={vi.fn()} busy={false} />);
    expect(screen.getByText(/bezogen auf den besten Monat/)).toBeDefined();
  });

  it('says when plantings had no interaction data', () => {
    const t = timeline({ plantings_without_interaction_data: 2 });
    render(<BloomTimeline timeline={t} forage onToggleForage={vi.fn()} busy={false} />);
    expect(screen.getByText(/keine Insektendaten/)).toBeDefined();
  });
});

describe('BloomTimeline — choosing a month', () => {
  function clickable(selected: number | null = null) {
    const onSelectMonth = vi.fn();
    render(
      <BloomTimeline
        timeline={timeline()}
        forage
        onToggleForage={vi.fn()}
        busy={false}
        selectedMonth={selected}
        onSelectMonth={onSelectMonth}
      />,
    );
    return onSelectMonth;
  }

  it('makes each month a real button, not a click handler on a row', () => {
    // A row is not focusable and announces nothing; a button is both.
    clickable();
    expect(screen.getByRole('button', { name: /Vorschläge für April/ })).toBeDefined();
  });

  it('selects the month that was clicked', () => {
    const onSelectMonth = clickable();
    screen.getByRole('button', { name: /Vorschläge für April/ }).click();
    expect(onSelectMonth).toHaveBeenCalledWith(4);
  });

  it('clicking the selected month again clears it', () => {
    // The same click that says "show me April" is the one reached for to undo it.
    const onSelectMonth = clickable(4);
    screen.getByRole('button', { name: /April/ }).click();
    expect(onSelectMonth).toHaveBeenCalledWith(null);
  });

  it('announces which month is selected', () => {
    clickable(4);
    const button = screen.getByRole('button', { name: /April/ });
    expect(button.getAttribute('aria-pressed')).toBe('true');
  });

  it('names the month in full, not the abbreviation the column shows', () => {
    // "Mär" is fine to read in a narrow column and wrong to hear read aloud.
    clickable();
    expect(screen.getByRole('button', { name: 'Vorschläge für März' })).toBeDefined();
  });

  it('offers months outside the gap season too', () => {
    // The gap analysis runs March to October; "what flowers in December" is
    // still a real question with a real answer.
    clickable();
    expect(screen.getByRole('button', { name: /Dezember/ })).toBeDefined();
  });

  it('stays a plain table when no handler is given', () => {
    // The timeline is used read-only elsewhere; it must not sprout buttons.
    render(<BloomTimeline timeline={timeline()} forage onToggleForage={vi.fn()} busy={false} />);
    expect(screen.queryByRole('button', { name: /Vorschläge für/ })).toBeNull();
  });
});
