import { useEffect, useState } from 'react';

/**
 * The value, once it has been there for `delayMs` — and null at once when it goes.
 *
 * For a sign that something is under way: most requests answer in well under a
 * third of a second, and a spinner that flashes up and vanishes for each of
 * them is a flicker, not information. Once shown it follows the value, so a
 * second request starting behind the first changes the words, not the timing.
 */
export function useShownAfter<T>(value: T | null, delayMs: number): T | null {
  const [due, setDue] = useState(false);
  const waiting = value !== null;

  useEffect(() => {
    if (!waiting) {
      setDue(false);
      return undefined;
    }
    const timer = window.setTimeout(() => setDue(true), delayMs);
    return () => window.clearTimeout(timer);
  }, [waiting, delayMs]);

  return due && value !== null ? value : null;
}
