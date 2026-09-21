import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { GardenOut, ShadowDay, TimelineOut } from './api/client';
import {
  details,
  fakeClient,
  openWorkspace,
  resetApp,
  start,
  stubMatchMedia,
} from './testing/appFixtures';
import { garden, lightMap } from './testing/gardens';

/* The owner's check (2026-09-21): the day plays under the chip that chose it,
   and every wait says that something is happening (docs 65, 87). */

function day(month = 6): ShadowDay {
  return { month, day: 15, frames: [{ minute: 600, altitude: 40, azimuth: 150, polygons: [] }] };
}

const dock = () => screen.getByRole('contentinfo');

/** The garden open, its sun map over the plan, and Tagesverlauf chosen. */
async function watchTheDay(overrides: Record<string, unknown> = {}) {
  const shadowDay = vi.fn(async (_token: string, month: number) => day(month));
  const client = fakeClient({ lightMap: vi.fn(async () => lightMap()), shadowDay, ...overrides });
  await openWorkspace(client);
  const shade = screen.getByRole('button', { name: 'Sonne & Schatten' });
  await waitFor(() => expect((shade as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(shade);
  fireEvent.click(within(details()).getByRole('button', { name: 'Tagesverlauf' }));
  await within(details()).findByRole('button', { name: 'Tag abspielen' });
  return { client, shadowDay };
}

beforeEach(stubMatchMedia);
afterEach(resetApp);

describe('App — the day plays in the sun panel', () => {
  it('puts the day’s play button in the details, and leaves the dock the year', async () => {
    await watchTheDay();
    expect(within(dock()).queryByRole('button', { name: 'Tag abspielen' })).toBeNull();
    expect(within(dock()).getByRole('button', { name: 'Jahr abspielen' })).toBeDefined();
  });

  it('watches the month the panel’s Zeitraum names, June for the whole season', async () => {
    const { shadowDay } = await watchTheDay();
    expect(shadowDay).toHaveBeenLastCalledWith('tok', 6);
    fireEvent.change(within(details()).getByRole('combobox', { name: 'Zeitraum' }), {
      target: { value: '4' },
    });
    await waitFor(() => expect(shadowDay).toHaveBeenLastCalledWith('tok', 4));
  });

  it('does not fetch the day again when the dock steps through the year', async () => {
    // It used to follow the bloom filter: playing the year refetched the day
    // and threw it back to dawn every half second.
    const { shadowDay } = await watchTheDay();
    const calls = shadowDay.mock.calls.length;
    fireEvent.click(within(dock()).getByRole('button', { name: 'Nächster Monat' }));
    fireEvent.click(within(dock()).getByRole('button', { name: 'Nächster Monat' }));
    await within(details()).findByRole('button', { name: 'Tag abspielen' });
    expect(shadowDay).toHaveBeenCalledTimes(calls);
  });

  it('says so when the day cannot be computed', async () => {
    const client = fakeClient({
      lightMap: vi.fn(async () => lightMap()),
      shadowDay: vi.fn(async () => {
        throw new Error('500: kaputt');
      }),
    });
    await openWorkspace(client);
    const shade = screen.getByRole('button', { name: 'Sonne & Schatten' });
    await waitFor(() => expect((shade as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(shade);
    fireEvent.click(within(details()).getByRole('button', { name: 'Tagesverlauf' }));
    expect(await within(details()).findByText('Tagesverlauf konnte nicht berechnet werden.'))
      .toBeDefined();
  });
});

describe('App — saying that something is happening', () => {
  it('holds the places of the garden’s panels while its answers are on the way', async () => {
    const never = () => new Promise<never>(() => undefined);
    const client = fakeClient({
      timeline: vi.fn((): Promise<TimelineOut> => never()),
      score: vi.fn(never),
      lightMap: vi.fn(never),
    });
    start(client, '#tok');
    await screen.findByRole('complementary', { name: 'Details' });
    for (const panel of ['steps', 'shade', 'score']) {
      expect(details().querySelector(`[data-skeleton="${panel}"]`)).not.toBeNull();
    }
    expect(dock().querySelector('[data-skeleton="timeline"]')).not.toBeNull();
  });

  it('lets the placeholders go once the garden has loaded', async () => {
    await openWorkspace(fakeClient());
    expect(document.querySelector('[data-skeleton]')).toBeNull();
  });

  it('lays a sweep over the plan while the shade is computed, and says when it is done', async () => {
    let finish: (map: ReturnType<typeof lightMap>) => void = () => undefined;
    const client = fakeClient({
      lightMap: vi.fn(async () => lightMap()),
      rebuildLightMap: vi.fn(() => new Promise((resolve) => { finish = resolve; })),
    });
    await openWorkspace(client);
    fireEvent.click(await within(details()).findByRole('button', { name: 'Schatten neu berechnen' }));
    expect(screen.getByTestId('plan-working').textContent).toMatch(/Schatten wird berechnet/);
    expect(within(details()).getByRole('button', { name: 'Wird berechnet…' })).toBeDefined();

    finish(lightMap());
    expect(await screen.findByText('Schatten berechnet.')).toBeDefined();
    expect(screen.queryByTestId('plan-working')).toBeNull();
  });

  it('says a garden is being opened while it comes from its link', async () => {
    let found: (value: GardenOut) => void = () => undefined;
    const client = fakeClient({
      getGarden: vi.fn(() => new Promise<GardenOut>((resolve) => { found = resolve; })),
    });
    start(client, '#tok');
    const main = await screen.findByRole('main');
    expect(within(main).getByText('Garten wird geöffnet…')).toBeDefined();

    found(garden('tok', 'Testgarten'));
    await screen.findByText('Testgarten geladen.');
    expect(screen.queryByText('Garten wird geöffnet…')).toBeNull();
  });
});
