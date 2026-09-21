import { useCallback, useEffect, useRef } from 'react';

import type { LightMap } from '../api/client';

/**
 * „Schatten berechnen“ from a bed's suggestions (owner review #9): the sun
 * panel's own rebuild, and the list re-read once the new map has arrived.
 *
 * `rebuild` does not say when it is done, so the map arriving is the sign — a
 * map other than the one there was when the button was pressed. A rebuild that
 * fails leaves the map as it was, and the list as it was with it; the status
 * line has already said why.
 */
export function useComputeShade(
  lightMap: LightMap | null,
  rebuild: () => void,
  afterShade: () => void,
): () => void {
  const asked = useRef<{ before: LightMap | null } | null>(null);

  const computeShade = useCallback(() => {
    asked.current = { before: lightMap };
    rebuild();
  }, [lightMap, rebuild]);

  useEffect(() => {
    const waiting = asked.current;
    if (waiting === null || waiting.before === lightMap) return;
    asked.current = null;
    afterShade();
  }, [lightMap, afterShade]);

  return computeShade;
}
