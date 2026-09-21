import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { NinaNaturClient, ShadowDay } from '../api/client';
import { useDay } from '../garden/useDay';
import { DayPlayer, clockTime } from './DayPlayer';

/** Four frames, half an hour apart from 06:00 UTC — 08:00 on a German clock in June. */
function day(): ShadowDay {
  return {
    month: 6,
    day: 15,
    frames: [360, 390, 420, 450].map((minute) => ({
      minute, altitude: 20, azimuth: 90, polygons: [],
    })),
  };
}

/** 12 s over four frames. */
const FRAME_MS = 3000;

function matchMedia(reducedMotion: boolean) {
  return (query: string) =>
    ({
      matches: reducedMotion && query.includes('prefers-reduced-motion'),
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      onchange: null,
      dispatchEvent: vi.fn(),
    }) as unknown as MediaQueryList;
}

interface HarnessProps {
  client: NinaNaturClient;
  setStatus: (text: string, tone?: 'info' | 'problem') => void;
  active?: boolean;
  inView?: boolean;
}

/** The player with the real hook behind it: the frames advance in `useDay`. */
function Harness({ client, setStatus, active = true, inView = true }: HarnessProps) {
  const watch = useDay(client, 'tok', active, 6, inView, setStatus);
  return <DayPlayer watch={watch} />;
}

function clientWith(shadowDay: () => Promise<ShadowDay>) {
  const fetch = vi.fn(shadowDay);
  return { client: { shadowDay: fetch } as unknown as NinaNaturClient, fetch };
}

/** Lets the fetched day land. */
async function settle() {
  await act(async () => {
    await Promise.resolve();
  });
}

async function show(options: { reduced?: boolean; shadowDay?: () => Promise<ShadowDay> } = {}) {
  vi.stubGlobal('matchMedia', matchMedia(options.reduced ?? false));
  const { client, fetch } = clientWith(options.shadowDay ?? (async () => day()));
  const setStatus = vi.fn();
  const view = render(<Harness client={client} setStatus={setStatus} />);
  await settle();
  const rerender = (props: Partial<HarnessProps>) =>
    view.rerender(<Harness client={client} setStatus={setStatus} {...props} />);
  return { fetch, setStatus, rerender };
}

const scrubber = () => screen.getByRole('slider', { name: 'Uhrzeit' }) as HTMLInputElement;
const tick = (ms: number) => act(() => {
  vi.advanceTimersByTime(ms);
});

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('DayPlayer — playing the day', () => {
  it('walks the day when played, and shows the clock time', async () => {
    await show();
    expect(screen.getByText('08:00 Uhr')).toBeDefined();
    fireEvent.click(screen.getByRole('button', { name: 'Tag abspielen' }));
    tick(FRAME_MS);
    expect(scrubber().value).toBe('1');
    expect(screen.getByText('08:30 Uhr')).toBeDefined();
  });

  it('goes round to dawn again after dusk', async () => {
    await show();
    fireEvent.click(screen.getByRole('button', { name: 'Tag abspielen' }));
    tick(FRAME_MS * 4);
    expect(scrubber().value).toBe('0');
  });

  it('stops when paused', async () => {
    await show();
    fireEvent.click(screen.getByRole('button', { name: 'Tag abspielen' }));
    tick(FRAME_MS);
    fireEvent.click(screen.getByRole('button', { name: 'Anhalten' }));
    tick(FRAME_MS * 3);
    expect(scrubber().value).toBe('1');
    expect(screen.getByRole('button', { name: 'Tag abspielen' })).toBeDefined();
  });

  it('carries on from wherever the scrubber was put', async () => {
    await show();
    fireEvent.click(screen.getByRole('button', { name: 'Tag abspielen' }));
    fireEvent.change(scrubber(), { target: { value: '2' } });
    tick(FRAME_MS);
    expect(scrubber().value).toBe('3');
  });

  it('stops, and stays stopped, when the panel is hidden', async () => {
    // Selecting a bed hides the sun panel; a day playing behind it would be a
    // timer nobody can reach.
    const { rerender } = await show();
    fireEvent.click(screen.getByRole('button', { name: 'Tag abspielen' }));
    rerender({ inView: false });
    tick(FRAME_MS * 2);
    rerender({ inView: true });
    tick(FRAME_MS * 2);
    expect(scrubber().value).toBe('0');
    expect(screen.getByRole('button', { name: 'Tag abspielen' })).toBeDefined();
  });

  it('is gone when the day is left', async () => {
    const { rerender } = await show();
    rerender({ active: false });
    expect(screen.queryByRole('slider')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Tag abspielen' })).toBeNull();
  });
});

describe('DayPlayer — reduced motion', () => {
  it('offers only the scrubber', async () => {
    // A day that runs by itself is exactly the motion that setting exists for.
    await show({ reduced: true });
    expect(screen.queryByRole('button', { name: 'Tag abspielen' })).toBeNull();
    expect(scrubber()).toBeDefined();
  });

  it('still shows every moment by hand', async () => {
    await show({ reduced: true });
    fireEvent.change(scrubber(), { target: { value: '3' } });
    expect(screen.getByText('09:30 Uhr')).toBeDefined();
  });
});

describe('DayPlayer — waiting and failing', () => {
  it('says the day is being computed while it is', async () => {
    await show({ shadowDay: () => new Promise<ShadowDay>(() => undefined) });
    expect(screen.getByText('Tagesverlauf wird berechnet…')).toBeDefined();
    expect(screen.queryByRole('slider')).toBeNull();
  });

  it('says so when the day could not be computed, and offers to try again', async () => {
    let calls = 0;
    const { fetch, setStatus } = await show({
      shadowDay: async () => {
        calls += 1;
        if (calls === 1) throw new Error('500: kaputt');
        return day();
      },
    });
    expect(screen.getByText('Tagesverlauf konnte nicht berechnet werden.')).toBeDefined();
    expect(setStatus).toHaveBeenCalledWith('Tagesverlauf konnte nicht berechnet werden.', 'problem');

    fireEvent.click(screen.getByRole('button', { name: 'Noch einmal versuchen' }));
    await settle();
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(scrubber()).toBeDefined();
  });
});

describe('clockTime', () => {
  it('reads the server’s UTC minutes as a German clock does', () => {
    // 11:00 UTC is noon in March (CET) and one o'clock from April (CEST).
    expect(clockTime(3, 15, 660)).toBe('12:00');
    expect(clockTime(6, 15, 660)).toBe('13:00');
    expect(clockTime(10, 15, 660)).toBe('13:00');
  });
});
