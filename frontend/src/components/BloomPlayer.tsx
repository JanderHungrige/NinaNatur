import { useEffect, useRef, useState } from 'react';

interface Props {
  month: number | null;
  onSelectMonth: (month: number) => void;
  /** With the shade switch on, play walks a day instead of the year. One
   *  control, two meanings — so the label has to say which. */
  shadowDay?: {
    frames: number;
    frame: number;
    onFrame: (frame: number) => void;
  } | undefined;
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
export function BloomPlayer({ month, onSelectMonth, shadowDay }: Props) {
  const [playing, setPlaying] = useState(false);
  const reduced = prefersReducedMotion();
  const current = useRef(month ?? 0);
  current.current = month ?? current.current;
  const day = shadowDay;

  useEffect(() => {
    if (!playing) return undefined;
    if (day !== undefined) {
      // A day is far more frames than a year is months, so it steps faster —
      // twelve seconds sunrise to dusk, which is slow enough to follow a
      // shadow across a lawn and quick enough to watch twice.
      let frame = day.frame;
      const timer = setInterval(() => {
        frame = (frame + 1) % Math.max(1, day.frames);
        day.onFrame(frame);
      }, Math.round(12000 / Math.max(1, day.frames)));
      return () => clearInterval(timer);
    }
    const timer = setInterval(() => {
      current.current = (current.current % 12) + 1;
      onSelectMonth(current.current);
    }, STEP_MS);
    return () => clearInterval(timer);
    // `day.frame` deliberately absent: it changes on every tick, and depending
    // on it would tear the interval down and rebuild it each time.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, onSelectMonth, day?.frames, day?.onFrame, day !== undefined]);

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
            aria-label={shadowDay === undefined ? 'Jahr abspielen' : 'Tag abspielen'}
            onClick={() => setPlaying(true)}
          >
            {shadowDay === undefined ? '▶ Jahr abspielen' : '▶ Tag abspielen'}
          </button>
        ))}
    </div>
  );
}
