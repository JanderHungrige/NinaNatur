import { act, fireEvent, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { LightMap } from './api/client';
import { RELIT_ENDINGS, RELIT_POLL_MS } from './garden/useRebuild';
import { details, fakeClient, openWorkspace, resetApp, stubMatchMedia } from './testing/appFixtures';
import { lightMap } from './testing/gardens';

/* The owner's report (2026-09-28): the first "Sonne & Schatten" at a place ran
   for a long time and ended with nothing, and a second press began again. The
   server reads the ground, the buildings and the laser first — past the
   proxy's 90 s — and went on after the page had given up. It answers 202 now,
   and the page waits for it (doc 65), without holding the rest of the page. */

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
    await vi.advanceTimersByTimeAsync(RELIT_POLL_MS);
  });
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
    expect(lightStatus).toHaveBeenCalledTimes(2);
    expect(client.lightMap).toHaveBeenLastCalledWith('tok', null);
    expect(screen.getByText('Schatten berechnet.')).toBeDefined();
    expect(client.rebuildLightMap).toHaveBeenCalledTimes(1);
  });

  it('leaves the rest of the page free while it waits', async () => {
    // It waited inside `run`, which makes the page busy: for up to ten
    // minutes every drawing tool and undo stood disabled (review of c2ec593).
    await pressRebuild({
      lightStatus: vi.fn(async () => ({ running: true, failed: false, known: true })),
    });
    await waitOnePoll();

    const tools = screen.getAllByRole('button', { name: 'Rechteck' });
    expect(tools.length).toBeGreaterThan(0);
    for (const tool of tools) expect(tool.getAttribute('aria-disabled')).toBeNull();
    // Only the rebuild itself waits, and cannot be pressed twice.
    expect(within(details()).getByRole('button', { name: 'Wird berechnet…' })
      .hasAttribute('disabled')).toBe(true);
  });

  it('says so when the first analysis failed, and gives the button back', async () => {
    const lightStatus = vi.fn(async () => ({ running: false, failed: true, known: true }));
    await pressRebuild({ lightStatus });

    await waitOnePoll();

    expect(screen.getByText(RELIT_ENDINGS.failed)).toBeDefined();
    expect(screen.queryByText(/fehlgeschlagen: /)).toBeNull();
    expect(within(details()).getByRole('button', { name: 'Schatten neu berechnen' })
      .hasAttribute('disabled')).toBe(false);
  });
});

describe('App — a first analysis the server lost', () => {
  it('says it was interrupted rather than computed', async () => {
    // A deployment rolled the image mid-analysis: the job was gone, and "not
    // running" alone read as done — "Schatten berechnet." over no new map.
    const lightStatus = vi.fn(async () => ({ running: false, failed: false, known: false }));
    const client = await pressRebuild({ lightStatus });

    await waitOnePoll();

    expect(screen.getByText(RELIT_ENDINGS.lost)).toBeDefined();
    expect(screen.queryByText('Schatten berechnet.')).toBeNull();
    expect(client.lightMap).not.toHaveBeenCalledWith('tok', null);
  });
});

describe('App — a garden left while its first analysis ends', () => {
  it('lands nothing in it, and does not open it again', async () => {
    // Its map arrived after the gardener had gone home, and the garden, set
    // again with every bed's light, opened itself over the front page
    // (review of c2ec593).
    let deliver: (map: LightMap) => void = () => {};
    const season = new Promise<LightMap>((resolve) => {
      deliver = resolve;
    });
    const client = await pressRebuild({
      lightMap: vi.fn(async (_token: string, month?: number | null) =>
        (month === null ? season : lightMap())),
      lightStatus: vi.fn(async () => ({ running: false, failed: false, known: true })),
    });
    await waitOnePoll();
    expect(client.lightMap).toHaveBeenLastCalledWith('tok', null);

    fireEvent.click(screen.getByRole('button', { name: 'Zur Startseite' }));
    const reads = client.getGarden.mock.calls.length;
    await act(async () => {
      deliver(lightMap());
      await Promise.resolve();
    });

    expect(client.getGarden.mock.calls.length).toBe(reads);
    expect(screen.getByLabelText('Garten-ID')).toBeDefined();
    expect(screen.queryByRole('complementary', { name: 'Details' })).toBeNull();
  });
});
