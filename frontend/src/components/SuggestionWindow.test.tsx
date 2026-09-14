import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { BedSuggestions } from '../api/client';
import { SuggestionWindow } from './SuggestionWindow';

type Suggestion = BedSuggestions['items'][number];
type Props = Parameters<typeof SuggestionWindow>[0];

const many = (count = 50): Suggestion[] =>
  Array.from({ length: count }, (_, i) =>
    ({
      taxon_id: i + 1, canonical_name: `Art ${i + 1}`, family: null, height_max_m: null,
      flowering_start_month: 5, flowering_end_month: 6, flower_colour: null, colour_known: false,
      bird_partners: null, space_m2: null, fits_bed: true, fit: { score: 0.5, axes: {} },
    }) as Suggestion,
  );

/** The window at a fixed size — jsdom lays nothing out, so it is told — and a
 *  way to hand it a list again, as the refetch after planting does. */
function show(props: Partial<Props> = {}) {
  const fixed: Props = {
    items: many(), label: 'Vorschläge', busy: false, viewportPx: 400, rowPx: 56,
    onPlant: vi.fn(async () => {}), onShowInfo: vi.fn(), ...props,
  };
  const view = render(<SuggestionWindow {...fixed} />);
  return { ...fixed, again: (changes: Partial<Props>) => view.rerender(<SuggestionWindow {...fixed} {...changes} />) };
}

const rows = () => within(screen.getByRole('list', { name: 'Vorschläge' })).getAllByRole('listitem');
const focusedAt = () => document.activeElement?.getAttribute('aria-posinset');
const press = (key: string) => fireEvent.keyDown(document.activeElement!, { key });

function focusLast() {
  rows()[0]!.focus();
  press('End');
}

describe('SuggestionWindow', () => {
  it('puts fewer than thirty of fifty rows in the document', () => {
    // Doc 90: 28 panel-rows made 7,480 px of details; the window renders what it shows.
    show();
    expect(rows().length).toBeGreaterThan(0);
    expect(rows().length).toBeLessThan(30);
  });

  it('says how long the list is, although most rows are not there', () => {
    show();
    expect(rows()[0]?.getAttribute('aria-setsize')).toBe('50');
    expect(rows()[0]?.getAttribute('aria-posinset')).toBe('1');
  });

  it('is one stop in the tab order', () => {
    show();
    const stops = rows().filter((row) => row.tabIndex === 0);
    expect(stops.map((row) => row.getAttribute('aria-posinset'))).toEqual(['1']);
  });

  it('reaches the last row with End, and the row is there when it takes the focus', () => {
    show();
    focusLast();
    expect(focusedAt()).toBe('50');
    expect(document.activeElement?.textContent).toMatch(/Art 50/);
  });

  it('moves a row with the arrows, a window with Page Down, and home with Home', () => {
    show();
    rows()[0]!.focus();
    press('ArrowDown');
    expect(focusedAt()).toBe('2');
    press('PageDown');
    // Seven whole rows of 56 px fit in 400 px.
    expect(focusedAt()).toBe('9');
    press('ArrowUp');
    expect(focusedAt()).toBe('8');
    press('Home');
    expect(focusedAt()).toBe('1');
  });

  it('walks every row with the keyboard', () => {
    show();
    rows()[0]!.focus();
    const reached: string[] = [];
    for (let step = 0; step < 49; step += 1) {
      press('ArrowDown');
      reached.push(focusedAt() ?? '');
    }
    expect(reached).toEqual(Array.from({ length: 49 }, (_, i) => String(i + 2)));
  });

  it('plants from the row the keyboard reached', () => {
    const { onPlant } = show();
    focusLast();
    fireEvent.click(within(document.activeElement as HTMLElement).getByRole('button', { name: 'Art 50 pflanzen' }));
    expect(onPlant).toHaveBeenCalledWith(50, 'Art 50');
  });

  it('keeps the tab stop in the document when the list is scrolled away from it', () => {
    show();
    const scroller = document.querySelector('.suggestion-window')!;
    Object.defineProperty(scroller, 'scrollTop', { value: 2000, writable: true, configurable: true });
    fireEvent.scroll(scroller);
    expect(rows().some((row) => row.getAttribute('aria-posinset') === '40')).toBe(true);
    const stops = rows().filter((row) => row.tabIndex === 0);
    expect(stops.map((row) => row.getAttribute('aria-posinset'))).toEqual(['1']);
    expect(rows().length).toBeLessThan(30);
  });

  it('keeps its place and its focus when the same list comes back', () => {
    // Rows are keyed by species (doc 90, rule 10).
    const { again } = show();
    focusLast();
    again({ items: many() });
    expect(focusedAt()).toBe('50');
  });

  it('gives the focus to the row that takes its place when the focused row leaves', () => {
    // A planted species is no longer suggested for its bed, so the row that was
    // pressed is gone when the list comes back.
    const { again } = show();
    focusLast();
    press('ArrowUp');
    expect(document.activeElement?.textContent).toMatch(/Art 49/);
    again({ items: many().filter((item) => item.taxon_id !== 49) });
    expect(focusedAt()).toBe('49');
    expect(document.activeElement?.textContent).toMatch(/Art 50/);
  });

  it('leaves the focus where it went once it has left the list', () => {
    const { again } = show();
    rows()[0]!.focus();
    (document.activeElement as HTMLElement).blur();
    again({ items: many().slice(1) });
    expect(document.activeElement).toBe(document.body);
  });

  it('gives every row a third line when any row has room or birds to show', () => {
    // One height for every row is what keeps the arithmetic exact.
    const items = many();
    items[30] = { ...items[30]!, bird_partners: 12 };
    show({ items });
    expect(rows().every((row) => row.classList.contains('suggestion-row--extra'))).toBe(true);
  });

  it('keeps two lines when no row needs a third', () => {
    show();
    expect(rows().some((row) => row.classList.contains('suggestion-row--extra'))).toBe(false);
  });

  it('draws nothing for an empty list', () => {
    show({ items: [] });
    expect(screen.queryByRole('list')).toBeNull();
  });
});
