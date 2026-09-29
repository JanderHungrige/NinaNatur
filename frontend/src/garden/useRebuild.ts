import { useCallback, useEffect, useRef, useState } from 'react';

import type { GardenOut, LightMap, NinaNaturClient, RelightStatus } from '../api/client';
import type { Status } from '../useStatus';

/*
 * "Schatten neu berechnen", from the press to the map on the plan (doc 65).
 *
 * The first time at a place the server reads the ground, the building model and
 * the laser before the light — longer than a request may wait. It answers 202
 * then, goes on, and is asked after: the page used to take the proxy's 504 for
 * the end, and a second press began it all again (the owner, 2026-09-28).
 *
 * Only the requests go through `run`. The wait did too at first, and `run` is
 * what makes the whole page busy: for up to ten minutes every drawing tool and
 * undo stood disabled (review of c2ec593). While it waits, only the rebuild's
 * own flag is set, which its buttons and the Zeitraum read.
 */

/** How often a relight left running is asked after, and for how long at most. */
export const RELIT_POLL_MS = 3000;
export const RELIT_PATIENCE_MS = 10 * 60 * 1000;
/** Status requests in a row that may go unanswered before the page stops
 *  asking: a deployment answers 502 for a few seconds, and after it that the
 *  job is gone — which is the thing to tell the gardener. */
export const RELIT_MISSES = 5;

const FIRST_ANALYSIS = 'Erste Analyse läuft – Gelände, Gebäude und Laserdaten werden geladen. '
  + 'Das kann einige Minuten dauern…';

/** What the page says when a relight it waited for ended without a map. */
export const RELIT_ENDINGS = {
  failed: 'Die erste Analyse ist fehlgeschlagen – bitte später noch einmal starten.',
  // A restart — a deployment rolling the image — loses a job. "Not running"
  // alone read as done, and said "Schatten berechnet." over no new map.
  lost: 'Die Berechnung wurde unterbrochen – bitte noch einmal starten.',
  slow: 'Die erste Analyse dauert ungewöhnlich lange und läuft auf dem Server weiter – '
    + 'bitte später noch einmal starten.',
} as const;

type Ending = 'done' | 'left' | keyof typeof RELIT_ENDINGS;

/**
 * The rebuild, its flag while it runs, and how many rebuilds have landed: the
 * list's own "Schatten berechnen" waits for that count to move rather than for
 * any new map, which a refresh during the rebuild also brings (review,
 * 2026-09-21). A rebuild that fails never counts.
 */
export function useRebuild(
  client: NinaNaturClient,
  token: string,
  status: Status,
  /** Makes way for the season a rebuild brings, and hands back how to land it. */
  expectSeason: () => (season: LightMap | null) => void,
  setGarden: (garden: GardenOut) => void,
) {
  const { run, setStatus } = status;
  const [rebuilding, setRebuilding] = useState(false);
  const [rebuilt, setRebuilt] = useState(0);
  const alive = useAlive();
  /** A press while one runs starts nothing: four buttons can start it, and a
   *  second wait beside the first would say everything twice. */
  const running = useRef(false);

  const rebuild = useCallback(() => {
    if (running.current) {
      setStatus('Schatten werden noch berechnet…');
      return;
    }
    running.current = true;
    setRebuilding(true);
    // The longest wait in the garden, so it is said when it starts as well as
    // when it ends.
    setStatus('Schatten wird berechnet…');
    const job: Job = {
      client, token, run, setStatus, alive, setGarden,
      land: expectSeason(),
      counted: () => setRebuilt((n) => n + 1),
    };
    void relight(job).finally(() => {
      running.current = false;
      setRebuilding(false);
    });
  }, [client, token, run, setStatus, alive, expectSeason, setGarden]);

  return { rebuild, rebuilding, rebuilt };
}

/** One press, and everything it needs to reach the plan. */
interface Job {
  client: NinaNaturClient;
  token: string;
  run: Status['run'];
  setStatus: Status['setStatus'];
  /** Whether the garden is still open. Nothing lands in one that was left. */
  alive: { readonly current: boolean };
  land: (season: LightMap | null) => void;
  setGarden: (garden: GardenOut) => void;
  counted: () => void;
}

/** One press, from the request to the map on the plan. Every failure is said
 *  — by `run`, or here where the wait is outside it — and none is thrown. */
async function relight(job: Job): Promise<void> {
  const { client, token, run, setStatus, alive } = job;
  // The button computes and stores the season. Coming back to a month view
  // afterwards would show a figure the button did not produce.
  const answer = await yielded(run, 'Schatten neu berechnen', async () => {
    const reply = await client.rebuildLightMap(token);
    if (!reply.pending) await landSeason(job, reply.map);
    return reply;
  });
  if (answer === null || !answer.pending || !alive.current) return;

  setStatus(FIRST_ANALYSIS);
  let ended: Ending;
  try {
    ended = await untilRelit(client, token, alive);
  } catch (error) {
    if (alive.current) {
      setStatus(`Der Server antwortet nicht (${(error as Error).message}) – `
        + 'bitte später noch einmal starten.', 'problem');
    }
    return;
  }
  if (ended === 'left') return;
  if (ended !== 'done') {
    setStatus(RELIT_ENDINGS[ended], 'problem');
    return;
  }
  await run('Schatten laden', async () => landSeason(job, await client.lightMap(token, null)));
}

/**
 * The season onto the plan, and the garden read again: the rebuild wrote every
 * bed's light too, and without reading it a bed went on saying "noch nicht
 * berechnet" beside a map just computed (the owner's check, 2026-09-21).
 *
 * Nothing lands in a garden that was left meanwhile: the garden, set again,
 * opened it again over the page the gardener had gone to (review of c2ec593).
 */
async function landSeason(job: Job, season: LightMap | null): Promise<void> {
  if (!job.alive.current) return;
  job.land(season);
  const fresh = await job.client.getGarden(job.token);
  if (!job.alive.current) return;
  if (fresh !== null) job.setGarden(fresh);
  job.counted();
  job.setStatus('Schatten berechnet.');
}

/**
 * Ask after a relight the server went on with, until it ends, the garden is
 * left or patience runs out. A status request that fails is asked again, and
 * thrown once `RELIT_MISSES` in a row have.
 */
async function untilRelit(
  client: NinaNaturClient,
  token: string,
  alive: { readonly current: boolean },
): Promise<Ending> {
  let misses = 0;
  for (let waited = 0; waited < RELIT_PATIENCE_MS; waited += RELIT_POLL_MS) {
    await new Promise((resolve) => setTimeout(resolve, RELIT_POLL_MS));
    if (!alive.current) return 'left';
    let state: RelightStatus;
    try {
      state = await client.lightStatus(token);
    } catch (error) {
      misses += 1;
      if (misses >= RELIT_MISSES) throw error;
      console.warn('Stand der Schattenberechnung nicht erfragt', error);
      continue;
    }
    misses = 0;
    if (!alive.current) return 'left';
    if (state.failed) return 'failed';
    if (!state.known) return 'lost';
    if (!state.running) return 'done';
  }
  return 'slow';
}

/** `run`, handing back what the action produced — null where it failed, which
 *  `run` has said. */
async function yielded<T>(
  run: Status['run'],
  label: string,
  action: () => Promise<T>,
): Promise<T | null> {
  const produced: { value: T | null } = { value: null };
  await run(label, async () => {
    produced.value = await action();
  });
  return produced.value;
}

/** Whether this garden is still open. Its workspace is keyed by the garden's
 *  token, so leaving it, or opening another, unmounts this. */
function useAlive(): { readonly current: boolean } {
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  return alive;
}
