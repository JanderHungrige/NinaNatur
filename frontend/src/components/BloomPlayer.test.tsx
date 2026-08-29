import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { BloomPlayer } from './BloomPlayer';

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

function show(reducedMotion = false) {
  vi.stubGlobal('matchMedia', matchMedia(reducedMotion));
  const onSelectMonth = vi.fn();
  render(<BloomPlayer month={null} onSelectMonth={onSelectMonth} />);
  return onSelectMonth;
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('BloomPlayer', () => {
  it('offers a month stepper', () => {
    show();
    expect(screen.getByRole('button', { name: 'Nächster Monat' })).toBeDefined();
    expect(screen.getByRole('button', { name: 'Voriger Monat' })).toBeDefined();
  });

  it('steps to the next month', () => {
    const onSelectMonth = show();
    fireEvent.click(screen.getByRole('button', { name: 'Nächster Monat' }));
    expect(onSelectMonth).toHaveBeenCalledWith(1);
  });

  it('runs the year when played', () => {
    const onSelectMonth = show();
    fireEvent.click(screen.getByRole('button', { name: 'Jahr abspielen' }));
    act(() => {
      vi.advanceTimersByTime(1300);
    });
    expect(onSelectMonth).toHaveBeenCalled();
  });

  it('stops when asked', () => {
    const onSelectMonth = show();
    fireEvent.click(screen.getByRole('button', { name: 'Jahr abspielen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Anhalten' }));
    onSelectMonth.mockClear();
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(onSelectMonth).not.toHaveBeenCalled();
  });

  it('does not offer autoplay when motion is reduced', () => {
    // An autoplaying year is exactly the motion that setting exists for.
    show(true);
    expect(screen.queryByRole('button', { name: 'Jahr abspielen' })).toBeNull();
  });

  it('keeps the stepper when motion is reduced', () => {
    // The feature still works; it just does not move on its own.
    show(true);
    expect(screen.getByRole('button', { name: 'Nächster Monat' })).toBeDefined();
  });
});
