import { useCallback, useState } from 'react';

function read(key: string, initial: boolean): boolean {
  try {
    const stored = window.localStorage.getItem(key);
    if (stored === null) return initial;
    const parsed: unknown = JSON.parse(stored);
    // Only a yes-or-no counts: an older build's string, or somebody's hand in
    // the devtools, must not become a layout nobody chose.
    return typeof parsed === 'boolean' ? parsed : initial;
  } catch {
    return initial;
  }
}

/**
 * A layout choice this browser remembers — whether the details are wide, whether
 * the year is folded away (doc 87).
 *
 * Kept in `localStorage`, which can be missing or throw: a private window, a
 * blocked site, a thumbnail capture. The choice is then simply not kept and
 * still applies for this visit. Nothing about a garden is ever stored here.
 */
export function useRemembered(key: string, initial: boolean): [boolean, (next: boolean) => void] {
  const [value, setValue] = useState(() => read(key, initial));

  const remember = useCallback(
    (next: boolean) => {
      setValue(next);
      try {
        window.localStorage.setItem(key, JSON.stringify(next));
      } catch {
        // Not kept for next time; nothing else depends on it.
      }
    },
    [key],
  );

  return [value, remember];
}
