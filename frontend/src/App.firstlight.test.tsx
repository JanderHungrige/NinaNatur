import { act, fireEvent, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { RELIT_POLL_MS } from './garden/useLight';
import { details, fakeClient, openWorkspace, resetApp, stubMatchMedia } from './testing/appFixtures';
import { lightMap } from './testing/gardens';

/* The owner's report (2026-09-28): the first "Sonne & Schatten" at a place ran
   for a long time and ended with nothing, and a second press began again. The
   server reads the ground, the buildings and the laser first — past the
   proxy's 90 s — and went on after the page had given up. It answers 202 now,
   and the page waits for it (doc 65). */

beforeEach(stubMatchMedia);
afterEach(() => {
  vi.useRealTimers();
  resetApp();
});

/** The garden open, its map built once, and the rebuild pressed. */
async function pressRebuild(overrides: Record<string, unknown>) {
  const client = fakeClient({
    lightMap: vi.fn(async () => lightMap()),
    rebuildLightMap: vi.fn(async () => ({ map: null, pending: true })),
    ...overrides,
  });
  await openWorkspace(client);
  const rebuild = await within(details()).findByRole('button', { name: 'Schatten neu berechnen' });
  // The page's own waits only: the queries above wait on real timers.
  vi.useFakeTimers({ toFake: ['setTimeout'] });
  fireEvent.click(rebuild);
  await act(async () => Promise.resolve());
  return client;
}

async function waitOnePoll() {
  await act(async () => {
    vi.advanceTimersByTime(RELIT_POLL_MS);
  });
  await act(async () => Promise.resolve());
}

describe('App — the first analysis at a place', () => {
  it('keeps waiting while the server goes on, says so, and shows the map once it is done', async () => {
    const lightStatus = vi.fn()
      .mockResolvedValueOnce({ running: true, failed: false, known: true })
      .mockResolvedValue({ running: false, failed: false, known: true });
    const client = await pressRebuild({ lightStatus });
    expect(screen.getAllByText(/Erste Analyse läuft/).length).toBeGreaterThan(0);
    expect(within(details()).getByRole('button', { name: 'Wird berechnet…' })).toBeDefined();

    await waitOnePoll();
    expect(lightStatus).toHaveBeenCalledTimes(1);
    expect(screen.queryByText('Schatten berechnet.')).toBeNull();

    await waitOnePoll();
    await act(async () => Promise.resolve());
    expect(lightStatus).toHaveBeenCalledTimes(2);
    expect(client.lightMap).toHaveBeenLastCalledWith('tok', null);
    expect(screen.getByText('Schatten berechnet.')).toBeDefined();
    expect(client.rebuildLightMap).toHaveBeenCalledTimes(1);
  });

  it('says so when the first analysis failed, and gives the button back', async () => {
    const lightStatus = vi.fn(async () => ({ running: false, failed: true, known: true }));
    await pressRebuild({ lightStatus });

    await waitOnePoll();
    await act(async () => Promise.resolve());

    expect(screen.getByText(/die erste Analyse ist fehlgeschlagen/)).toBeDefined();
    expect(within(details()).getByRole('button', { name: 'Schatten neu berechnen' }))
      .toBeDefined();
  });
});

describe('App — a first analysis the server lost', () => {
  it('says it was interrupted rather than computed', async () => {
    // A deployment rolled the image mid-analysis: the job was gone, and "not
    // running" alone read as done — "Schatten berechnet." over no new map.
    const lightStatus = vi.fn(async () => ({ running: false, failed: false, known: false }));
    const client = await pressRebuild({ lightStatus });

    await waitOnePoll();
    await act(async () => Promise.resolve());

    expect(screen.getByText(/die Berechnung wurde unterbrochen/)).toBeDefined();
    expect(screen.queryByText('Schatten berechnet.')).toBeNull();
    expect(client.lightMap).not.toHaveBeenCalledWith('tok', null);
  });
});
