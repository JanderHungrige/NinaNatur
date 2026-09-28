import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { GardenOut, LightMap, NinaNaturClient, RelightStatus } from '../api/client';
import { lightMap } from '../testing/gardens';
import { useStatus } from '../useStatus';
import { RELIT_ENDINGS, RELIT_MISSES, RELIT_PATIENCE_MS, RELIT_POLL_MS, useRebuild } from './useRebuild';

/* The rebuild's wait for a first analysis, on its own (doc 65): that it holds
   nothing but itself, what it says when it ends without a map, and that it
   stops once nobody is left to tell (review of c2ec593). */

const running: RelightStatus = { running: true, failed: false, known: true };
const done: RelightStatus = { running: false, failed: false, known: true };

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout'] });
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function mount(lightStatus: () => Promise<RelightStatus>) {
  const client = {
    rebuildLightMap: vi.fn(async () => ({ map: null, pending: true })),
    lightStatus: vi.fn(lightStatus),
    lightMap: vi.fn(async () => lightMap()),
    getGarden: vi.fn(async () => ({ share_token: 'tok' }) as unknown as GardenOut),
  };
  const land = vi.fn<(season: LightMap | null) => void>();
  const setGarden = vi.fn<(garden: GardenOut) => void>();
  const expectSeason = () => land;
  const hook = renderHook(() => {
    const status = useStatus();
    const rebuild = useRebuild(
      client as unknown as NinaNaturClient, 'tok', status, expectSeason, setGarden,
    );
    return { status, ...rebuild };
  });
  return { client, land, setGarden, hook };
}

type Mounted = ReturnType<typeof mount>['hook'];

async function press(hook: Mounted) {
  await act(async () => {
    hook.result.current.rebuild();
    await Promise.resolve();
  });
}

async function wait(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe('useRebuild — waiting for a first analysis', () => {
  it('holds only its own flag, not the page, and starts nothing on a second press', async () => {
    const { client, hook } = mount(async () => running);
    await press(hook);
    await wait(RELIT_POLL_MS);
    expect(hook.result.current.rebuilding).toBe(true);
    expect(hook.result.current.status.busy).toBe(false);

    await press(hook);
    expect(client.rebuildLightMap).toHaveBeenCalledTimes(1);
    expect(hook.result.current.status.status.text).toBe('Schatten werden noch berechnet…');
  });

  it('stops asking once the garden is left, and lands nothing in it', async () => {
    const { client, land, setGarden, hook } = mount(async () => running);
    await press(hook);
    await wait(RELIT_POLL_MS);
    const asked = client.lightStatus.mock.calls.length;
    expect(asked).toBe(1);

    hook.unmount();
    await wait(RELIT_POLL_MS * 5);

    expect(client.lightStatus).toHaveBeenCalledTimes(asked);
    expect(land).not.toHaveBeenCalled();
    expect(setGarden).not.toHaveBeenCalled();
  });

  it('sets no garden once it is left while being read again', async () => {
    // The garden set again opened it again over the page the gardener had
    // gone to (review of c2ec593).
    let deliver: (garden: GardenOut) => void = () => {};
    const { client, land, setGarden, hook } = mount(async () => done);
    client.getGarden.mockImplementation(() => new Promise<GardenOut>((resolve) => {
      deliver = resolve;
    }));
    await press(hook);
    await wait(RELIT_POLL_MS);
    expect(land).toHaveBeenCalledTimes(1);

    hook.unmount();
    await act(async () => {
      deliver({ share_token: 'tok' } as unknown as GardenOut);
      await Promise.resolve();
    });

    expect(setGarden).not.toHaveBeenCalled();
    expect(hook.result.current.rebuilt).toBe(0);
  });

  it('says when patience has run out that it goes on — not that it failed', async () => {
    const { land, hook } = mount(async () => running);
    await press(hook);
    await wait(RELIT_PATIENCE_MS);

    const said = hook.result.current.status.status;
    expect(said).toMatchObject({ text: RELIT_ENDINGS.slow, tone: 'problem' });
    expect(said.text).not.toMatch(/fehlgeschlagen/);
    expect(hook.result.current.rebuilding).toBe(false);
    expect(land).not.toHaveBeenCalled();
  });

  it('rides out a few questions that go unanswered, as while a deployment rolls', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    let asked = 0;
    const { land, hook } = mount(async () => {
      asked += 1;
      if (asked < RELIT_MISSES) throw new Error('502');
      return done;
    });
    await press(hook);
    await wait(RELIT_POLL_MS * RELIT_MISSES);

    expect(land).toHaveBeenCalledTimes(1);
    expect(hook.result.current.rebuilt).toBe(1);
    expect(hook.result.current.status.status.text).toBe('Schatten berechnet.');
  });

  it('and says the server does not answer once too many in a row have not', async () => {
    const warned = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const { client, land, hook } = mount(async () => {
      throw new Error('502 Bad Gateway');
    });
    await press(hook);
    await wait(RELIT_POLL_MS * (RELIT_MISSES + 3));

    expect(client.lightStatus).toHaveBeenCalledTimes(RELIT_MISSES);
    expect(warned).toHaveBeenCalledTimes(RELIT_MISSES - 1);
    const said = hook.result.current.status.status;
    expect(said.tone).toBe('problem');
    expect(said.text).toMatch(/^Der Server antwortet nicht \(502 Bad Gateway\)/);
    expect(hook.result.current.rebuilding).toBe(false);
    expect(land).not.toHaveBeenCalled();
  });
});
