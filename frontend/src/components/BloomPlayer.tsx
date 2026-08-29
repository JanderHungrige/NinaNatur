import { useEffect, useRef, useState } from 'react';

interface Props {
  month: number | null;
  onSelectMonth: (month: number) => void;
}

/** ~7 seconds for twelve months, as the wave plan asks. */
const STEP_MS = Math.round(7000 / 12);

function prefersReducedMotion(): boolean {
  try {
    return globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
  } catch {
    // A browser that cannot answer is not a reason to start moving.
    return true;
  }
}

/**
 * Stepping and playing through the bloom year.
 *
 * The month it lands on is the same `floweringMonth` the filter bar shows and
 * the timeline marks — one piece of state, three ways in. A second "playback
 * month" would drift from the filter the moment either could be cleared alone.
 */
export function BloomPlayer({ month, onSelectMonth }: Props) {
  const [playing, setPlaying] = useState(false);
  const reduced = prefersReducedMotion();
  const current = useRef(month ?? 0);
  current.current = month ?? current.current;

  useEffect(() => {
    if (!playing) return undefined;
    const timer = setInterval(() => {
      current.current = (current.current % 12) + 1;
      onSelectMonth(current.current);
    }, STEP_MS);
    return () => clearInterval(timer);
  }, [playing, onSelectMonth]);

  const step = (delta: number) => {
    const next = (((month ?? 0) + delta + 11) % 12) + 1;
    onSelectMonth(next);
  };

  return (
    <div className="bloom-player">
      <button type="button" aria-label="Voriger Monat" onClick={() => step(-1)}>
        ‹
      </button>
      <button type="button" aria-label="Nächster Monat" onClick={() => step(1)}>
        ›
      </button>

      {/* No autoplay under prefers-reduced-motion: a year that runs by itself is
          exactly the motion that setting exists for. The stepper stays, so the
          feature works — it just does not move on its own. */}
      {!reduced &&
        (playing ? (
          <button type="button" aria-label="Anhalten" onClick={() => setPlaying(false)}>
            ⏸ Anhalten
          </button>
        ) : (
          <button
            type="button"
            aria-label="Jahr abspielen"
            onClick={() => setPlaying(true)}
          >
            ▶ Jahr abspielen
          </button>
        ))}
    </div>
  );
}
