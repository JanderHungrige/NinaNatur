import { useEffect, useState } from 'react';

/** A message that needs nothing from anyone, or one that reports a failure. */
export type StatusTone = 'info' | 'problem';

export interface StatusMessage {
  text: string;
  tone: StatusTone;
  /** Counts every message, so the same words said twice are two messages. */
  stamp: number;
}

const MS_PER_CHARACTER = 70;
const SHORTEST_MS = 5000;
const LONGEST_MS = 15_000;

/** How long a message stays: long enough to read, never so long it becomes furniture. */
export function readingTime(text: string): number {
  return Math.min(LONGEST_MS, Math.max(SHORTEST_MS, text.length * MS_PER_CHARACTER));
}

/**
 * What just happened, where it can be seen.
 *
 * It used to be a line at the very foot of the page: announced to a screen
 * reader, and out of sight for anyone scrolling a list three screens up (doc
 * 86). The live region is always in the page — a region that appears together
 * with its first message is often not announced — and the words inside it are
 * keyed by the message's stamp, so saying the same thing again announces it
 * again.
 */
export function StatusToast({ message }: { message: StatusMessage }) {
  // The stamp of the message that has gone, by timing out or by being closed.
  const [gone, setGone] = useState<number | null>(null);

  useEffect(() => {
    // A failure waits for the person; everything else waits for nobody.
    if (message.text === '' || message.tone === 'problem') return undefined;
    const timer = window.setTimeout(() => setGone(message.stamp), readingTime(message.text));
    return () => window.clearTimeout(timer);
  }, [message]);

  const shown = message.text !== '' && gone !== message.stamp;
  const classes = ['status-toast'];
  if (shown) classes.push('status-toast--shown');
  if (message.tone === 'problem') classes.push('status-toast--problem');

  return (
    <div className={classes.join(' ')}>
      <p className="status-toast__text" role="status" aria-live="polite">
        {shown ? <span key={message.stamp}>{message.text}</span> : null}
      </p>
      {shown && message.tone === 'problem' ? (
        // Outside the live region, so its label is never read as part of the message.
        <button
          type="button"
          className="status-toast__close"
          onClick={() => setGone(message.stamp)}
        >
          Schließen
        </button>
      ) : null}
    </div>
  );
}
