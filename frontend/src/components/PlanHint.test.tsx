import { act, render } from '@testing-library/react';
import { useLayoutEffect } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { HINT_VISIBLE_MS, PlanHint } from './PlanHint';

/* The owner, 2026-09-21: "Wähle eine Form und …" was always in the picture.
   Seven seconds, then it fades; another tool's hint shows again. */

beforeEach(() => {
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

const hint = (container: HTMLElement) => container.querySelector('.plan-hint')!;

describe('PlanHint', () => {
  it('shows the hint, and fades it after seven seconds', () => {
    const { container } = render(<PlanHint text="Wähle eine Form" />);
    expect(hint(container).classList.contains('plan-hint--faded')).toBe(false);

    act(() => vi.advanceTimersByTime(HINT_VISIBLE_MS - 1));
    expect(hint(container).classList.contains('plan-hint--faded')).toBe(false);
    act(() => vi.advanceTimersByTime(1));
    expect(hint(container).classList.contains('plan-hint--faded')).toBe(true);
  });

  it('shows a new hint again, for seven seconds of its own', () => {
    const { container, rerender } = render(<PlanHint text="Wähle eine Form" />);
    act(() => vi.advanceTimersByTime(HINT_VISIBLE_MS));

    rerender(<PlanHint text="Aufziehen." />);
    expect(hint(container).textContent).toBe('Aufziehen.');
    expect(hint(container).classList.contains('plan-hint--faded')).toBe(false);
    act(() => vi.advanceTimersByTime(HINT_VISIBLE_MS));
    expect(hint(container).classList.contains('plan-hint--faded')).toBe(true);
  });

  it('shows a hint that comes back, however soon — seven seconds each time', () => {
    // Drawing a shape puts the tool down within a second or two, and the select
    // hint says what to do next: it must not return already faded (review,
    // 2026-09-21).
    const { container, rerender } = render(<PlanHint text="Wähle eine Form" />);
    act(() => vi.advanceTimersByTime(HINT_VISIBLE_MS));
    rerender(<PlanHint text="Aufziehen." />);
    act(() => vi.advanceTimersByTime(2_000));

    rerender(<PlanHint text="Wähle eine Form" />);
    expect(hint(container).classList.contains('plan-hint--faded')).toBe(false);
    act(() => vi.advanceTimersByTime(HINT_VISIBLE_MS - 1));
    expect(hint(container).classList.contains('plan-hint--faded')).toBe(false);
    act(() => vi.advanceTimersByTime(1));
    expect(hint(container).classList.contains('plan-hint--faded')).toBe(true);
  });

  it('counts its seven seconds only while it can be seen', () => {
    // The phone's raised sheet hides it with display: none; a hint that ran out
    // there was never read.
    const observers: Array<(entries: Array<{ isIntersecting: boolean }>) => void> = [];
    vi.stubGlobal('IntersectionObserver', class {
      constructor(callback: (entries: Array<{ isIntersecting: boolean }>) => void) {
        observers.push(callback);
      }
      observe() {}
      disconnect() {}
    });
    try {
      const { container } = render(<PlanHint text="Ecke für Ecke klicken" />);
      act(() => observers.forEach((notify) => notify([{ isIntersecting: false }])));
      act(() => vi.advanceTimersByTime(HINT_VISIBLE_MS * 3));
      expect(hint(container).classList.contains('plan-hint--faded')).toBe(false);

      act(() => observers.forEach((notify) => notify([{ isIntersecting: true }])));
      act(() => vi.advanceTimersByTime(HINT_VISIBLE_MS - 1));
      expect(hint(container).classList.contains('plan-hint--faded')).toBe(false);
      act(() => vi.advanceTimersByTime(1));
      expect(hint(container).classList.contains('plan-hint--faded')).toBe(true);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('waits while its tab is in the background', () => {
    const state = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden');
    try {
      const { container } = render(<PlanHint text="Wähle eine Form" />);
      act(() => vi.advanceTimersByTime(HINT_VISIBLE_MS * 2));
      expect(hint(container).classList.contains('plan-hint--faded')).toBe(false);

      state.mockReturnValue('visible');
      act(() => { document.dispatchEvent(new Event('visibilitychange')); });
      act(() => vi.advanceTimersByTime(HINT_VISIBLE_MS));
      expect(hint(container).classList.contains('plan-hint--faded')).toBe(true);
    } finally {
      state.mockRestore();
    }
  });

  it('stops counting when its tab is left mid-count, and starts over on return', () => {
    const state = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
    try {
      const { container } = render(<PlanHint text="Aufziehen." />);
      act(() => vi.advanceTimersByTime(5_000));
      state.mockReturnValue('hidden');
      act(() => { document.dispatchEvent(new Event('visibilitychange')); });
      act(() => vi.advanceTimersByTime(HINT_VISIBLE_MS * 3));
      expect(hint(container).classList.contains('plan-hint--faded')).toBe(false);

      state.mockReturnValue('visible');
      act(() => { document.dispatchEvent(new Event('visibilitychange')); });
      act(() => vi.advanceTimersByTime(HINT_VISIBLE_MS - 1));
      expect(hint(container).classList.contains('plan-hint--faded')).toBe(false);
      act(() => vi.advanceTimersByTime(1));
      expect(hint(container).classList.contains('plan-hint--faded')).toBe(true);
    } finally {
      state.mockRestore();
    }
  });

  it('notices a tab switched between its render and its listening', () => {
    // A sibling's layout effect runs in that gap: the switch it makes there is
    // the one a garden opened in a background tab and brought forward at once
    // would see (review, 2026-09-21).
    const state = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden');
    function Forward() {
      useLayoutEffect(() => {
        state.mockReturnValue('visible');
        document.dispatchEvent(new Event('visibilitychange'));
      }, []);
      return null;
    }
    try {
      const { container } = render(<><PlanHint text="Wähle eine Form" /><Forward /></>);
      act(() => vi.advanceTimersByTime(HINT_VISIBLE_MS));
      expect(hint(container).classList.contains('plan-hint--faded')).toBe(true);
    } finally {
      state.mockRestore();
    }
  });

  it('takes its listeners with it when it goes', () => {
    const added = vi.spyOn(document, 'addEventListener');
    const removed = vi.spyOn(document, 'removeEventListener');
    const disconnect = vi.fn();
    vi.stubGlobal('IntersectionObserver', class {
      observe() {}
      disconnect = disconnect;
    });
    try {
      render(<PlanHint text="Wähle eine Form" />).unmount();
      const listening = added.mock.calls.filter(([type]) => type === 'visibilitychange');
      expect(listening).toHaveLength(1);
      expect(removed.mock.calls.filter(([type]) => type === 'visibilitychange')
        .map(([, handler]) => handler)).toEqual(listening.map(([, handler]) => handler));
      expect(disconnect).toHaveBeenCalled();
    } finally {
      added.mockRestore();
      removed.mockRestore();
      vi.unstubAllGlobals();
    }
  });

  it('keeps one live region, so each new hint is read out', () => {
    const { container, rerender } = render(<PlanHint text="Wähle eine Form" />);
    const first = hint(container);
    rerender(<PlanHint text="Aufziehen." />);
    expect(hint(container)).toBe(first);
    expect(first.getAttribute('aria-live')).toBe('polite');
  });
});
