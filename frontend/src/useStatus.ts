import { useCallback, useRef, useState } from 'react';

import type { StatusMessage, StatusTone } from './components/StatusToast';

/** One request under way: its own number, so two with the same label are two. */
interface Pending {
  id: number;
  label: string;
}

/**
 * What the page last said, which requests are running, and the one wrapper
 * every change goes through.
 *
 * Site-wide rather than per garden (doc 87): a failure on the front door has to
 * reach the toast as surely as one inside a garden.
 *
 * `busy` is a list rather than a flag. As a flag, the first of two overlapping
 * requests to finish cleared it while the other was still running, and every
 * button came back while the page was still waiting.
 */
export function useStatus() {
  const [status, setMessage] = useState<StatusMessage>({ text: '', tone: 'info', stamp: 0 });
  const [pending, setPending] = useState<readonly Pending[]>([]);
  const counter = useRef(0);

  /** Every message is a new one, even in the same words — see StatusToast. */
  const setStatus = useCallback(
    (text: string, tone: StatusTone = 'info') =>
      setMessage((previous) => ({ text, tone, stamp: previous.stamp + 1 })),
    [],
  );

  /** Wrap every mutation so a failed request always reaches the live region. */
  const run = useCallback(
    async (label: string, action: () => Promise<void>) => {
      counter.current += 1;
      const id = counter.current;
      setPending((list) => [...list, { id, label }]);
      try {
        await action();
      } catch (error) {
        setStatus(`${label} fehlgeschlagen: ${(error as Error).message}`, 'problem');
      } finally {
        setPending((list) => list.filter((entry) => entry.id !== id));
      }
    },
    [setStatus],
  );

  const busy = pending.length > 0;
  /** What the newest running request is called, for the header to show (doc 87). */
  const working = pending.length > 0 ? pending[pending.length - 1]!.label : null;

  return { status, setStatus, busy, working, run };
}

/** What a garden's hooks are handed from the site: saying things, and running them. */
export type Status = Pick<ReturnType<typeof useStatus>, 'setStatus' | 'busy' | 'working' | 'run'>;
