import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { NinaNaturClient, ShadowDay } from '../api/client';
import { useDay } from '../garden/useDay';
import { DayPlayer } from './DayPlayer';

/*
 * From the integration review of the owner's check (2026-09-21): reduced
 * motion switched on mid-play hid the pause button and left the day running;
 * and "Noch einmal versuchen" removed itself while it held the focus.
 */

function day(): ShadowDay {
  return {
    month: 6, day: 15,
    frames: [360, 390, 420, 450].map((minute) => ({ minute, altitude: 20, azimuth: 90, polygons: [] })),
  };
}

const FRAME_MS = 3000;

/** A matchMedia whose reduced-motion answer can change while the page is open. */
function motionSetting() {
  const listeners: Array<(event: MediaQueryListEvent) => void> = [];
  let reduced = false;
  vi.stubGlobal('matchMedia', (query: string) => ({
    get matches() { return reduced && query.includes('prefers-reduced-motion'); },
    media: query,
    addEventListener: (_: string, listener: (event: MediaQueryListEvent) => void) => {
      listeners.push(listener);
    },
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    onchange: null,
    dispatchEvent: vi.fn(),
  }));
  return {
    reduce: () => act(() => {
      reduced = true;
      for (const listener of listeners) listener({ matches: true } as MediaQueryListEvent);
    }),
  };
}

/** `setStatus` is one function for the life of the player, as in the app: a
 *  new one each render would restart the day's fetch every time. */
function Harness({ client, setStatus }: { client: NinaNaturClient; setStatus: () => void }) {
  return <DayPlayer watch={useDay(client, 'tok', true, 6, true, setStatus)} />;
}

async function show(shadowDay: () => Promise<ShadowDay>) {
  const client = { shadowDay: vi.fn(shadowDay) } as unknown as NinaNaturClient;
  render(<Harness client={client} setStatus={vi.fn()} />);
  await settle();
}

/** Lets a fetched day, or its failure, land: a rejection takes a few ticks. */
async function settle() {
  await act(async () => {
    for (let tick = 0; tick < 5; tick += 1) await Promise.resolve();
  });
}

const scrubber = () => screen.getByRole('slider', { name: 'Uhrzeit' }) as HTMLInputElement;

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('DayPlayer — when the setting changes mid-play', () => {
  it('stops the day rather than hide the only way to stop it', async () => {
    const motion = motionSetting();
    await show(async () => day());
    fireEvent.click(screen.getByRole('button', { name: 'Tag abspielen' }));
    act(() => { vi.advanceTimersByTime(FRAME_MS); });
    expect(scrubber().value).toBe('1');

    motion.reduce();
    act(() => { vi.advanceTimersByTime(FRAME_MS * 2); });
    expect(scrubber().value).toBe('1');
    expect(screen.queryByRole('button', { name: /Anhalten|Tag abspielen/ })).toBeNull();
  });
});

describe('DayPlayer — trying again from the keyboard', () => {
  it('keeps the focus in the player while it waits, and hands it on after', async () => {
    motionSetting();
    let finish: (value: ShadowDay) => void = () => undefined;
    let calls = 0;
    await show(() => {
      calls += 1;
      if (calls === 1) return Promise.reject(new Error('500'));
      return new Promise<ShadowDay>((resolve) => { finish = resolve; });
    });
    const retry = screen.getByRole('button', { name: 'Noch einmal versuchen' });
    retry.focus();
    fireEvent.click(retry);

    expect(screen.getByText('Tagesverlauf wird berechnet…')).toBeDefined();
    expect(document.activeElement).not.toBe(document.body);
    expect(document.activeElement?.classList.contains('day-player')).toBe(true);

    finish(day());
    await settle();
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Tag abspielen' }));
  });
});
