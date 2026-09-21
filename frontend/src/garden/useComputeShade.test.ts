import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useComputeShade } from './useComputeShade';

/*
 * „Schatten berechnen“ from the suggestions (owner review #9): the sun panel's
 * rebuild, then the list re-read — only once that rebuild has landed, because a
 * list re-read before it would say "noch nicht berechnet" all over again.
 * `rebuilt` is how many rebuilds have landed (`useLight`).
 */

function setup(initial = 0) {
  const rebuild = vi.fn();
  const afterShade = vi.fn();
  const hook = renderHook(
    ({ rebuilt }: { rebuilt: number }) => useComputeShade(rebuilt, rebuild, afterShade),
    { initialProps: { rebuilt: initial } },
  );
  return { ...hook, rebuild, afterShade };
}

describe('useComputeShade', () => {
  it('rebuilds, and re-reads the list once the rebuild has landed', () => {
    const { result, rerender, rebuild, afterShade } = setup();
    act(() => result.current());
    expect(rebuild).toHaveBeenCalledTimes(1);
    expect(afterShade).not.toHaveBeenCalled();

    rerender({ rebuilt: 1 });
    expect(afterShade).toHaveBeenCalledTimes(1);

    // Once: the next rebuild is somebody else's business.
    rerender({ rebuilt: 2 });
    expect(afterShade).toHaveBeenCalledTimes(1);
  });

  it('does not re-read the list for a rebuild nobody asked for from it', () => {
    // The sun panel's own button.
    const { rerender, afterShade } = setup();
    rerender({ rebuilt: 1 });
    expect(afterShade).not.toHaveBeenCalled();
  });

  it('is not fooled by anything else re-rendering while it waits', () => {
    // A refresh during the rebuild brings a new map but no landed rebuild.
    const { result, rerender, afterShade } = setup(3);
    act(() => result.current());
    rerender({ rebuilt: 3 });
    rerender({ rebuilt: 3 });
    expect(afterShade).not.toHaveBeenCalled();
  });

  it('stays quiet after a rebuild that failed, whatever happens next', () => {
    // A failed rebuild never counts; the hook used to stay armed and re-read
    // the list at the next unrelated change of map.
    const { result, rerender, afterShade } = setup(5);
    act(() => result.current());
    rerender({ rebuilt: 5 });
    expect(afterShade).not.toHaveBeenCalled();
  });
});
