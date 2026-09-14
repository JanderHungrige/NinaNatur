import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { CanopySuggestion } from './api/client';
import {
  details,
  fakeClient,
  onPlan,
  openWorkspace,
  resetApp,
  stubMatchMedia,
  viewHeading,
} from './testing/appFixtures';
import { garden, lightMap, richGarden } from './testing/gardens';

/* Doc 89: three steps in, each empty panel one line, and the rest where it acts. */

const fresh = () => garden('tok', 'Neuer Garten', { beds: [] });
const ready = () => garden('tok', 'Testgarten', { soil_type: 'loam', moisture: 'fresh' });
const stepsShown = () => within(details()).queryByRole('region', { name: 'Drei Schritte zum Anfang' });
const tree = { suggestion_id: 9, x: 8, y: 6, radius_m: 3, height_m: 12.5 } as CanopySuggestion;

beforeEach(stubMatchMedia);
afterEach(resetApp);

describe('App — three steps in', () => {
  it('opens a garden nobody has set up on three steps, with nothing planted as one line', async () => {
    await openWorkspace(fakeClient({}, { tok: fresh() }), 'Neuer Garten');
    expect(stepsShown()).not.toBeNull();
    // The sun panel's only content without a map would be the step's own button.
    expect(within(details()).queryByRole('heading', { name: 'Sonne und Schatten' })).toBeNull();
    expect(within(details()).getByText(/Wähle ein Beet/)).toBeDefined();
  });

  it('arms Vieleck on the rail from the third step', async () => {
    await openWorkspace(fakeClient({}, { tok: fresh() }), 'Neuer Garten');
    fireEvent.click(within(details()).getByRole('button', { name: 'Beet zeichnen' }));
    expect(screen.getByRole('button', { name: 'Vieleck' }).getAttribute('aria-pressed')).toBe('true');
  });

  it('computes the shade from the second step, ticks it, and shows the sun panel', async () => {
    const client = fakeClient({ rebuildLightMap: vi.fn(async () => lightMap()) }, { tok: fresh() });
    await openWorkspace(client, 'Neuer Garten');
    fireEvent.click(within(details()).getByRole('button', { name: 'Schatten berechnen' }));
    await within(details()).findByRole('heading', { name: 'Sonne und Schatten' });
    const second = within(stepsShown() as HTMLElement).getAllByRole('listitem')[1];
    expect(second?.textContent).toMatch(/erledigt/);
  });

  it('shows no steps for a garden that is set up, and its soil as one line', async () => {
    await openWorkspace(fakeClient({ lightMap: vi.fn(async () => lightMap()) }, { tok: ready() }));
    await within(details()).findByRole('heading', { name: 'Sonne und Schatten' });
    expect(stepsShown()).toBeNull();
    expect(within(details()).getByRole('button', { name: 'Boden ändern' })).toBeDefined();
  });
});

describe('App — the rest, where it acts', () => {
  it('places a viewpoint with the rail’s Standpunkt, puts the tool down and says what is visible', async () => {
    const sightlines = vi.fn(async () => ({ plantings: [], estimated_count: 0 }));
    await openWorkspace(fakeClient({ sightlines }, { tok: ready() }));
    const standpoint = screen.getByRole('button', { name: 'Standpunkt' });
    fireEvent.click(standpoint);
    expect(standpoint.getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(screen.getByTestId('canvas-surface'), { clientX: 200, clientY: 150 });
    await within(details()).findByRole('heading', { name: 'Von hier aus sichtbar' });
    expect(sightlines).toHaveBeenCalledTimes(1);
    expect(standpoint.getAttribute('aria-pressed')).toBe('false');
  });

  it('marks the found trees on the plan, and shows their card from it', async () => {
    await openWorkspace(fakeClient({ canopies: vi.fn(async () => [tree]) }, { tok: richGarden() }));
    await waitFor(() => expect(document.querySelectorAll('.canopy-mark')).toHaveLength(1));
    fireEvent.click(onPlan('polygon[data-element-id="1"]'));
    fireEvent.click(screen.getByRole('button', { name: '1 gefundener Baum' }));
    expect(viewHeading()?.textContent).toBe('Testgarten');
    expect(document.activeElement).toBe(
      within(details()).getByRole('heading', { name: 'Bäume in der Nähe' }),
    );
  });

  it('offers the claim in the header’s fold to a signed-in account, and not in the details', async () => {
    const account = { username: 'nina', email: null, recovery_note: '' };
    await openWorkspace(fakeClient({ me: vi.fn(async () => account) }, { tok: ready() }));
    const header = screen.getByRole('banner');
    await within(header).findByRole('button', { name: 'Diesen Garten meinem Konto zuordnen' });
    expect(within(details()).queryByRole('button', { name: /Konto zuordnen/ })).toBeNull();
  });
});
