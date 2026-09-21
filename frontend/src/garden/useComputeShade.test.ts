import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { LightMap } from '../api/client';
import { lightMap } from '../testing/gardens';
import { useComputeShade } from './useComputeShade';

/*
 * „Schatten berechnen“ from the suggestions (owner review #9): the sun panel's
 * rebuild, then the list re-read — only once the new map is there, because a
 * list re-read before it would say "noch nicht berechnet" all over again.
 */

function setup(initial: LightMap | null) {
  const rebuild = vi.fn();
  const afterShade = vi.fn();
  const hook = renderHook(
    ({ map }: { map: LightMap | null }) => useComputeShade(map, rebuild, afterShade),
    { initialProps: { map: initial } },
  );
  return { ...hook, rebuild, afterShade };
}

describe('useComputeShade', () => {
  it('rebuilds, and re-reads the list once the new map has arrived', () => {
    const { result, rerender, rebuild, afterShade } = setup(null);
    act(() => result.current());
    expect(rebuild).toHaveBeenCalledTimes(1);
    expect(afterShade).not.toHaveBeenCalled();

    rerender({ map: lightMap() });
    expect(afterShade).toHaveBeenCalledTimes(1);

    // Once: the next map is somebody else's business.
    rerender({ map: lightMap() });
    expect(afterShade).toHaveBeenCalledTimes(1);
  });

  it('does not re-read the list for a map nobody asked for from it', () => {
    // The sun panel's own button, a month switched, a refresh after planting.
    const { rerender, afterShade } = setup(lightMap());
    rerender({ map: lightMap() });
    expect(afterShade).not.toHaveBeenCalled();
  });

  it('waits while the map is still the one there was when it was pressed', () => {
    const before = lightMap();
    const { result, rerender, afterShade } = setup(before);
    act(() => result.current());
    rerender({ map: before });
    expect(afterShade).not.toHaveBeenCalled();
  });
});
