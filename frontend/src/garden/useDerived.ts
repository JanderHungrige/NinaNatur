import { useCallback, useEffect, useMemo, useState } from 'react';

import type {
  BloomPalette,
  CanopySuggestion,
  Credit,
  GardenOut,
  ImprovementsOut,
  LightMap,
  NinaNaturClient,
  ScoreOut,
  Terrain,
  TimelineOut,
} from '../api/client';
import { type DerivedSetters, fetchDerived } from '../derived';
import type { Status } from '../useStatus';

/**
 * Everything the server derives from one garden, and the trees it found beside
 * it (doc 87). Fetched when the garden's workspace opens, re-read after edits.
 */
export function useDerived(
  client: NinaNaturClient,
  garden: GardenOut,
  setGarden: (garden: GardenOut) => void,
  status: Status,
  /** What to say once it has all arrived: "<name> geladen.", or what a map import found. */
  greeting: string,
) {
  const { run, setStatus } = status;
  const token = garden.share_token;
  const [timeline, setTimeline] = useState<TimelineOut | null>(null);
  const [score, setScore] = useState<ScoreOut | null>(null);
  const [improvements, setImprovements] = useState<ImprovementsOut | null>(null);
  const [palette, setPalette] = useState<BloomPalette | null>(null);
  /** The sun map. Fetched with the garden so the switch can say straight away
   *  whether there is anything to show. */
  const [lightMap, setLightMap] = useState<LightMap | null>(null);
  const [terrain, setTerrain] = useState<Terrain | null>(null);
  /** Which survey said so, and the credit its licence asks for (doc 106). */
  const [sources, setSources] = useState<Credit[]>([]);
  const [canopies, setCanopies] = useState<CanopySuggestion[]>([]);
  const [forage, setForage] = useState(true);
  /** Until the first answers are in: the details hold their places meanwhile. */
  const [loading, setLoading] = useState(true);

  /** Where each derived answer lands: the same six on opening and after every change. */
  const show = useMemo<DerivedSetters>(
    () => ({
      timeline: setTimeline,
      score: setScore,
      improvements: setImprovements,
      palette: setPalette,
      lightMap: setLightMap,
      terrain: setTerrain,
      sources: setSources,
    }),
    [],
  );

  // Opening the garden: all six at once (see `fetchDerived`) and the canopy
  // suggestions — they come with the garden, not after every edit, since an edit
  // does not move a tree — and then say it is open. A failure says so too;
  // before the split it reached nobody but the console.
  useEffect(() => {
    let current = true;
    Promise.all([fetchDerived(client, token, true, show), client.canopies(token).then(setCanopies)])
      .then(() => {
        if (!current) return;
        // With the greeting, not a tick after it: whatever reads "geladen"
        // finds the details in their places.
        setLoading(false);
        setStatus(greeting);
      })
      .catch((error: unknown) => {
        if (!current) return;
        setLoading(false);
        setStatus(`Laden fehlgeschlagen: ${(error as Error).message}`, 'problem');
      });
    return () => {
      current = false;
    };
    // Once per garden. The workspace is keyed by the token, so a new garden is a
    // new mount; a renamed one must not fetch everything again.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client, token]);

  /** Everything the server derives, re-read together after any change. */
  const refresh = useCallback(
    () => fetchDerived(client, token, forage, show),
    [client, token, forage, show],
  );

  const toggleForage = useCallback(
    (weighted: boolean) => {
      setForage(weighted);
      void run('Gewichtung wechseln', async () => {
        const next = await client.timeline(token, weighted);
        setTimeline(next);
        setStatus(
          next.gaps.length === 0
            ? 'Keine Lücke zwischen März und Oktober.'
            : `${next.gaps.length} Lücke(n) in dieser Ansicht.`,
        );
      });
    },
    [client, token, run, setStatus],
  );

  const acceptCanopy = useCallback(
    (id: number) =>
      void run('Baum eintragen', async () => {
        setGarden(await client.acceptCanopy(token, id));
        setCanopies(await client.canopies(token));
      }),
    [client, token, run, setGarden],
  );

  const dismissCanopy = useCallback(
    (id: number) =>
      void run('Vorschlag verwerfen', async () => {
        await client.dismissCanopy(token, id);
        setCanopies(await client.canopies(token));
      }),
    [client, token, run],
  );

  /**
   * The colour that actually applies to each species, hand entry included.
   *
   * The info panel needs it to tell "you entered violet" from "you entered
   * violet and a source has since said blue". Read from the palette, which is
   * where colour is resolved.
   */
  const resolvedColours = useMemo(() => {
    const map: Record<number, string | null> = {};
    for (const bed of palette?.beds ?? []) {
      for (const entry of bed.plantings) {
        if (entry.taxon_id !== null) map[entry.taxon_id] = entry.colour;
      }
    }
    return map;
  }, [palette]);

  return {
    loading,
    timeline,
    score,
    improvements,
    setImprovements,
    palette,
    lightMap,
    setLightMap,
    terrain,
    sources,
    canopies,
    forage,
    toggleForage,
    refresh,
    acceptCanopy,
    dismissCanopy,
    resolvedColours,
  };
}

export type Derived = ReturnType<typeof useDerived>;
