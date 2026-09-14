import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useRemembered } from './useRemembered';

const KEY = 'ninanatur.test.remembered';

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
});

describe('useRemembered', () => {
  it('starts from the default when nothing is stored', () => {
    const { result } = renderHook(() => useRemembered(KEY, false));
    expect(result.current[0]).toBe(false);
  });

  it('starts from what was stored last time', () => {
    window.localStorage.setItem(KEY, 'true');
    const { result } = renderHook(() => useRemembered(KEY, false));
    expect(result.current[0]).toBe(true);
  });

  it('keeps a change for next time', () => {
    const { result } = renderHook(() => useRemembered(KEY, false));
    act(() => result.current[1](true));
    expect(result.current[0]).toBe(true);
    expect(window.localStorage.getItem(KEY)).toBe('true');
  });

  it('ignores a stored value of the wrong kind', () => {
    // An older build, or somebody's hand in the devtools, must not turn a
    // yes-or-no into a string the layout does not know.
    window.localStorage.setItem(KEY, '"wide"');
    const { result } = renderHook(() => useRemembered(KEY, false));
    expect(result.current[0]).toBe(false);
  });

  it('still works where storage throws', () => {
    // A private window, a blocked site, a thumbnail capture: the choice is then
    // simply not kept, and the page still works.
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    const { result } = renderHook(() => useRemembered(KEY, true));
    expect(result.current[0]).toBe(true);
    act(() => result.current[1](false));
    expect(result.current[0]).toBe(false);
  });
});
