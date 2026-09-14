import { useCallback, useState } from 'react';

import type { StatusMessage, StatusTone } from './components/StatusToast';

/**
 * What the page last said, whether a request is running, and the one wrapper
 * every change goes through.
 *
 * Site-wide rather than per garden (doc 87): a failure on the front door has to
 * reach the toast as surely as one inside a garden.
 */
export function useStatus() {
  const [status, setMessage] = useState<StatusMessage>({ text: '', tone: 'info', stamp: 0 });
  const [busy, setBusy] = useState(false);

  /** Every message is a new one, even in the same words — see StatusToast. */
  const setStatus = useCallback(
    (text: string, tone: StatusTone = 'info') =>
      setMessage((previous) => ({ text, tone, stamp: previous.stamp + 1 })),
    [],
  );

  /** Wrap every mutation so a failed request always reaches the live region. */
  const run = useCallback(
    async (label: string, action: () => Promise<void>) => {
      setBusy(true);
      try {
        await action();
      } catch (error) {
        setStatus(`${label} fehlgeschlagen: ${(error as Error).message}`, 'problem');
      } finally {
        setBusy(false);
      }
    },
    [setStatus],
  );

  return { status, setStatus, busy, run };
}

/** What a garden's hooks are handed from the site: saying things, and running them. */
export type Status = Pick<ReturnType<typeof useStatus>, 'setStatus' | 'busy' | 'run'>;
