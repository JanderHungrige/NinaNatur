import { useCallback, useEffect, useRef } from 'react';

/**
 * „Schatten berechnen“ from a bed's suggestions (owner review #9): the sun
 * panel's own rebuild, and the list re-read once that rebuild has landed.
 *
 * It waits for the rebuild's own count to move (`useLight`'s `rebuilt`). It
 * used to wait for any new sun map, and a refresh during the rebuild — a
 * paste, a moved shape — brought one: the list was re-read before the server
 * had the new light, and a failed rebuild left the hook armed for the next
 * unrelated map (review, 2026-09-21). A rebuild that fails never counts.
 */
export function useComputeShade(
  rebuilt: number,
  rebuild: () => void,
  afterShade: () => void,
): () => void {
  const asked = useRef<number | null>(null);

  const computeShade = useCallback(() => {
    asked.current = rebuilt;
    rebuild();
  }, [rebuilt, rebuild]);

  useEffect(() => {
    if (asked.current === null || rebuilt <= asked.current) return;
    asked.current = null;
    afterShade();
  }, [rebuilt, afterShade]);

  return computeShade;
}
