import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { BedSuggestions } from './api/client';
import { details, fakeClient, onPlan, openWorkspace, resetApp, stubMatchMedia } from './testing/appFixtures';
import { garden, suggestions } from './testing/gardens';

/*
 * Doc 90: a bed's fifty suggestions as a window in its details — fewer rows in
 * the document than the list is long, every one of them in the keyboard's
 * reach, and the focus kept when planting takes a species out of the list.
 */

/** Fifty suggestions for the Südbeet, Art 1 to Art 50, less those planted. */
function listed(planted: ReadonlySet<number>): BedSuggestions {
  const one = suggestions().items[0]!;
  const items = Array.from({ length: 50 }, (_, i) => ({
    ...one, taxon_id: 100 + i, canonical_name: `Art ${i + 1}`,
  })).filter((item) => !planted.has(item.taxon_id));
  return { ...suggestions(), total: items.length, items };
}

beforeEach(stubMatchMedia);
afterEach(resetApp);

async function openBed() {
  const planted = new Set<number>();
  const client = fakeClient({
    bedSuggestions: vi.fn(async () => listed(planted)),
    // The server leaves a planted species out of its bed's suggestions.
    plant: vi.fn(async (_token: string, _bedId: number, taxonId: number) => {
      planted.add(taxonId);
      return garden('tok', 'Testgarten');
    }),
  });
  await openWorkspace(client);
  fireEvent.click(onPlan('polygon[data-element-id="1"]'));
  const list = await within(details()).findByRole('list', { name: 'Vorschläge' });
  return { client, list };
}

function focusLast(list: HTMLElement): HTMLElement {
  within(list).getAllByRole('listitem')[0]!.focus();
  fireEvent.keyDown(document.activeElement!, { key: 'End' });
  return document.activeElement as HTMLElement;
}

const focusedRow = () => document.activeElement?.closest('li[aria-posinset]');

describe('App — a list that fits a window', () => {
  it('shows a bed’s fifty suggestions with fewer than thirty rows in the document', async () => {
    const { list } = await openBed();
    const rows = within(list).getAllByRole('listitem');
    expect(rows.length).toBeLessThan(30);
    expect(rows[0]?.getAttribute('aria-setsize')).toBe('50');
  });

  it('reaches the fiftieth suggestion with the keyboard, and plants it', async () => {
    const { client, list } = await openBed();
    const last = focusLast(list);
    expect(last.getAttribute('aria-posinset')).toBe('50');
    fireEvent.click(within(last).getByRole('button', { name: 'Art 50 pflanzen' }));
    await screen.findByText('Art 50 gepflanzt.');
    expect(client.plant).toHaveBeenCalledWith('tok', 1, 149);
  });

  it('keeps the focus in the list when the planted species leaves it', async () => {
    const { list } = await openBed();
    fireEvent.click(within(focusLast(list)).getByRole('button', { name: 'Art 50 pflanzen' }));
    await screen.findByText('Art 50 gepflanzt.');
    // Art 50 is gone, and the row now last holds the focus.
    await waitFor(() => expect(focusedRow()?.getAttribute('aria-setsize')).toBe('49'));
    expect(focusedRow()?.getAttribute('aria-posinset')).toBe('49');
    expect(focusedRow()?.textContent).toMatch(/Art 49/);
  });

  it('keeps the filters in the list’s header, above the rows', async () => {
    const { list } = await openBed();
    const header = list.closest('section')?.querySelector('.suggestions__header');
    expect(header?.textContent).toMatch(/Keine Filter aktiv/);
    expect(header?.compareDocumentPosition(list)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });
});
