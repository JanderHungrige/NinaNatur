import { useCallback, useEffect, useState } from 'react';

import type { NinaNaturClient, ShadowDay } from '../api/client';
import type { Status } from '../useStatus';

/** Sunrise to dusk in twelve seconds: slow enough to follow a shadow across a
 *  lawn, quick enough to watch twice. */
export const DAY_MS = 12_000;

/**
 * One day's shadows, being watched (docs 65, 87).
 *
 * Fetched only while it is actually watched — the shade on and Tagesverlauf
 * chosen — for the month the panel's Zeitraum names, June for the whole season.
 * The play state lives here rather than in the button, so the button can stand
 * in the panel under the chips while the plan it moves is elsewhere, and so
 * anything that hides the panel can stop it.
 *
 * Stopping is what every change does. A new month is a new question, and its
 * shadows start from nothing; leaving the day, switching the shade off or
 * selecting something that hides the panel stops the playback and leaves it
 * stopped. A timer running behind a hidden control is one nobody can reach.
 */
export function useDay(
  client: NinaNaturClient,
  token: string,
  /** The shade is on and Tagesverlauf is chosen. */
  active: boolean,
  month: number,
  /** The panel with the day's controls is on screen. */
  inView: boolean,
  setStatus: Status['setStatus'],
) {
  const fetched = useShadowDay(client, token, active, month, setStatus);
  const { shadows } = fetched;
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    setFrame(0);
    if (shadows === null) setPlaying(false);
  }, [shadows]);

  useEffect(() => {
    if (!inView) setPlaying(false);
  }, [inView]);

  useEffect(() => {
    if (!playing || shadows === null) return undefined;
    const count = Math.max(1, shadows.frames.length);
    // From wherever the frame is now, so a scrub while playing carries on from
    // the scrub rather than jumping back.
    const timer = window.setInterval(
      () => setFrame((current) => (current + 1) % count),
      Math.round(DAY_MS / count),
    );
    return () => window.clearInterval(timer);
  }, [playing, shadows]);

  const play = useCallback(() => setPlaying(true), []);
  const pause = useCallback(() => setPlaying(false), []);

  return { ...fetched, frame, setFrame, playing: playing && shadows !== null, play, pause };
}

export type DayWatch = ReturnType<typeof useDay>;

/** The day's shadows from the server, whether they are on their way, and
 *  whether they failed to come. */
function useShadowDay(
  client: NinaNaturClient,
  token: string,
  active: boolean,
  month: number,
  setStatus: Status['setStatus'],
) {
  const [shadows, setShadows] = useState<ShadowDay | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    setShadows(null);
    setFailed(false);
    setLoading(active);
    if (!active) return undefined;
    let dropped = false;
    client
      .shadowDay(token, month)
      .then((day) => {
        if (dropped) return;
        setShadows(day);
        setLoading(false);
      })
      .catch(() => {
        if (dropped) return;
        setLoading(false);
        setFailed(true);
        // Said, where it used to be swallowed: the play button simply never
        // turned up, and nothing said why.
        setStatus('Tagesverlauf konnte nicht berechnet werden.', 'problem');
      });
    return () => {
      // A month switched twice in a second must not have the first answer
      // arrive last and win.
      dropped = true;
    };
  }, [client, token, active, month, attempt, setStatus]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { shadows, loading, failed, retry };
}
