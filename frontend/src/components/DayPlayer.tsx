import type { DayWatch } from '../garden/useDay';
import { usePrefersReducedMotion } from '../usePrefersReducedMotion';
import { Working } from './Working';

interface Props {
  watch: DayWatch;
}

/**
 * The clock time of a frame, as the gardener's watch shows it.
 *
 * The server counts a frame's minutes from midnight UTC (`solar/day.py`), so
 * 11:00 there is noon in March and one in the afternoon from April on. The
 * 15th of the months the model covers never falls on a change of the clocks,
 * which makes the year irrelevant; one is needed for the date all the same.
 */
export function clockTime(month: number, dayOfMonth: number, minute: number): string {
  const at = new Date(Date.UTC(2026, month - 1, dayOfMonth, 0, minute));
  return at.toLocaleTimeString('de-DE', {
    timeZone: 'Europe/Berlin', hour: '2-digit', minute: '2-digit',
  });
}

/**
 * Playing the day's shadows, in the panel where the day was chosen (doc 65).
 *
 * It used to be the dock's play button changing its meaning once the day had
 * arrived — at the other end of the page from the chip that asked for it, and
 * with nothing at all while the day was computed or when it failed.
 *
 * The scrubber is always there, so any moment can be looked at by hand; under
 * `prefers-reduced-motion` it is the only control, because a day that runs by
 * itself is exactly the motion that setting exists for.
 */
export function DayPlayer({ watch }: Props) {
  const reduced = usePrefersReducedMotion();
  const { shadows, frame, loading, failed } = watch;

  if (loading) {
    return (
      <div className="day-player">
        <Working label="Tagesverlauf wird berechnet…" />
      </div>
    );
  }
  if (failed) {
    return (
      <div className="day-player">
        <p className="hint day-player__problem">Tagesverlauf konnte nicht berechnet werden.</p>
        <button type="button" className="chip" onClick={watch.retry}>
          Noch einmal versuchen
        </button>
      </div>
    );
  }
  if (shadows === null) return null;
  if (shadows.frames.length === 0) {
    return <p className="hint">An diesem Tag steht die Sonne nie hoch genug für Schatten.</p>;
  }

  const last = shadows.frames.length - 1;
  const shown = shadows.frames[Math.min(frame, last)]!;
  const time = clockTime(shadows.month, shadows.day, shown.minute);

  return (
    <div className="day-player" role="group" aria-label="Tagesverlauf abspielen">
      {!reduced && <PlayButton playing={watch.playing} onPlay={watch.play} onPause={watch.pause} />}
      <input
        type="range"
        className="day-player__scrubber"
        min={0}
        max={last}
        step={1}
        value={Math.min(frame, last)}
        aria-label="Uhrzeit"
        aria-valuetext={`${time} Uhr`}
        onChange={(event) => watch.setFrame(Number(event.target.value))}
      />
      <output className="day-player__time">{time} Uhr</output>
    </div>
  );
}

function PlayButton({ playing, onPlay, onPause }: {
  playing: boolean; onPlay: () => void; onPause: () => void;
}) {
  return playing ? (
    <button type="button" className="chip" onClick={onPause}>
      <span aria-hidden="true">⏸</span> Anhalten
    </button>
  ) : (
    <button type="button" className="chip" onClick={onPlay}>
      <span aria-hidden="true">▶</span> Tag abspielen
    </button>
  );
}
