import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { Landcover } from './api/client';
import { fakeClient, openWorkspace, resetApp, stubMatchMedia } from './testing/appFixtures';
import { lightMap } from './testing/gardens';

/* The land around the garden, fetched as decoration (doc 114): it never holds
   up the garden, never fails it, and comes again after a shade rebuild. */

const WOOD: Landcover = {
  attribution: '© OpenStreetMap-Mitwirkende',
  licence: 'ODbL-1.0',
  areas: [{ kind: 'wood', rings: [[[20, 20], [60, 20], [60, 60], [20, 60]]] }],
};

const layer = () => document.querySelector('[data-testid="landcover"]');

beforeEach(stubMatchMedia);
afterEach(resetApp);

describe('App — the land around the garden', () => {
  it('draws it on the plan once it has arrived', async () => {
    await openWorkspace(fakeClient({ landcover: vi.fn(async () => WOOD) }));
    await waitFor(() => expect(layer()?.querySelectorAll('.landcover__area')).toHaveLength(1));
  });

  it('does not hold up the garden while it is on its way', async () => {
    // Never answered: the garden opens and says so all the same.
    await openWorkspace(fakeClient({ landcover: vi.fn(() => new Promise(() => {})) }));
    expect(screen.getByText('Testgarten geladen.')).toBeDefined();
    expect(layer()).toBeNull();
  });

  it('does not call a garden that loaded a failure when only its surroundings failed', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    await openWorkspace(fakeClient({ landcover: vi.fn(async () => { throw new Error('502'); }) }));
    await waitFor(() => expect(warn).toHaveBeenCalled());
    expect(screen.queryByText(/Laden fehlgeschlagen/)).toBeNull();
    warn.mockRestore();
  });

  it('asks again for land still on its way, and draws it once it is there', async () => {
    // The server fetches it after answering: the first ask finds none yet.
    const EMPTY: Landcover = { ...WOOD, areas: [] };
    const landcover = vi.fn().mockResolvedValueOnce(EMPTY).mockResolvedValue(WOOD);
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      await openWorkspace(fakeClient({ landcover }));
      expect(landcover).toHaveBeenCalledTimes(1);
      await vi.advanceTimersByTimeAsync(5_000);
      await waitFor(() => expect(layer()?.querySelectorAll('.landcover__area')).toHaveLength(1));
      expect(landcover).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });

  it('asks again once a shade rebuild has landed — where an older garden first gets it', async () => {
    const landcover = vi.fn(async () => WOOD);
    const client = fakeClient({ landcover, rebuildLightMap: vi.fn(async () => lightMap()) });
    await openWorkspace(client);
    expect(landcover).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Sonne & Schatten' }));
    await waitFor(() => expect(landcover).toHaveBeenCalledTimes(2));
  });
});
