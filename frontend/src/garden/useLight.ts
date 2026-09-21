import { useCallback, useRef, useState } from 'react';

import type { GardenOut, LightMap, NinaNaturClient, SightlinesOut } from '../api/client';
import type { MapMode } from '../components/SunMap';
import type { Status } from '../useStatus';
import { useDay } from './useDay';

/** The month a day is watched in while the Zeitraum is the whole season. */
const SEASON_DAY_MONTH = 6;

/**
 * Light over one garden: the sun map and what it shows, the day being watched,
 * and what is visible from where somebody stands (doc 87).
 */
export function useLight(
  client: NinaNaturClient,
  token: string,
  status: Status,
  setLightMap: (map: LightMap | null) => void,
  /** Whether the garden's own details — the shade switch among them — are showing. */
  inView: boolean,
  /** The garden as the server now has it: a rebuild writes every bed's light. */
  setGarden: (garden: GardenOut) => void,
) {
  const { run, setStatus } = status;
  const [shadeOn, setShadeOn] = useState(false);
  const [mapMode, setMapMode] = useState<MapMode>('hours');
  const sunMap = useSunMap(client, token, status, setLightMap, setGarden);
  const [sightlines, setSightlines] = useState<SightlinesOut | null>(null);
  const [viewpoint, setViewpoint] = useState<{ x: number; y: number } | null>(null);

  /**
   * The day's shadows, for the month the panel's Zeitraum names. It used to
   * follow the bloom filter, so playing the year in the dock refetched the day
   * and threw its frame back to dawn every half second. `mapMode === 'day'`
   * is the whole gate: the two heat maps are read, not watched.
   */
  const day = useDay(
    client,
    token,
    shadeOn && mapMode === 'day',
    sunMap.mapMonth ?? SEASON_DAY_MONTH,
    inView,
    setStatus,
  );

  /** Standing somewhere and asking what is visible. Computed on the server,
   *  because it needs plant heights from the catalogue. */
  const lookFrom = useCallback(
    (x: number, y: number) => {
      setViewpoint({ x, y });
      void run('Sichtprüfung', async () => {
        setSightlines(await client.sightlines(token, { x, y }));
      });
    },
    [client, token, run],
  );

  const clearSightlines = useCallback(() => {
    setSightlines(null);
    setViewpoint(null);
  }, []);

  return {
    shadeOn,
    // Leaving the map also leaves the day: the two are one question, and a day
    // playing behind a hidden map is a timer nobody can see. `useDay` sees the
    // switch go off and stops.
    toggleShade: setShadeOn,
    mapMode,
    setMapMode,
    ...sunMap,
    day,
    sightlines,
    viewpoint,
    lookFrom,
    clearSightlines,
  };
}

export type Light = ReturnType<typeof useLight>;

/**
 * The sun map itself: which period it answers for, and computing it again —
 * each with a flag for while it is under way, so the panel and the plan can
 * say so instead of sitting still (doc 65).
 */
function useSunMap(
  client: NinaNaturClient,
  token: string,
  status: Status,
  setLightMap: (map: LightMap | null) => void,
  setGarden: (garden: GardenOut) => void,
) {
  const { run, setStatus } = status;
  // Null is the whole season, which is the number a plant is placed by.
  const [mapMonth, setMapMonth] = useState<number | null>(null);
  const [monthLoading, setMonthLoading] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  /** The newest month asked for. Two switches in a second send two requests,
   *  and only the last one's answer may land or clear the flag. */
  const latestMonth = useRef(0);

  const changeMonth = useCallback(
    (next: number | null) => {
      setMapMonth(next);
      latestMonth.current += 1;
      const asked = latestMonth.current;
      setMonthLoading(true);
      void run('Zeitraum wechseln', async () => {
        try {
          const map = await client.lightMap(token, next);
          if (asked === latestMonth.current) setLightMap(map);
        } finally {
          if (asked === latestMonth.current) setMonthLoading(false);
        }
      });
    },
    [client, token, run, setLightMap],
  );

  /** How many rebuilds have landed: the list's own "Schatten berechnen" waits
   *  for this to move rather than for any new map, which a refresh during the
   *  rebuild also brings (review, 2026-09-21). */
  const [rebuilt, setRebuilt] = useState(0);

  const rebuild = useCallback(() => {
    // A month still on its way would land on top of the season this stores.
    latestMonth.current += 1;
    const asked = latestMonth.current;
    setMonthLoading(false);
    setRebuilding(true);
    // The longest wait in the garden — terrain, buildings, laser points, then
    // the light — so it is said when it starts as well as when it ends.
    setStatus('Schatten wird berechnet…');
    void run('Schatten neu berechnen', async () => {
      try {
        // The button computes and stores the season. Coming back to a month
        // view afterwards would show a figure the button did not produce.
        const season = await client.rebuildLightMap(token);
        // The Zeitraum is locked while this runs; should a month have been
        // chosen anyway, its map stands, and the season does not cover it.
        if (asked === latestMonth.current) {
          setMapMonth(null);
          setLightMap(season);
        }
        // The rebuild wrote every bed's light too. Without reading the garden
        // again, a bed went on saying "noch nicht berechnet" beside a map that
        // had just been computed (the owner's check, 2026-09-21).
        const fresh = await client.getGarden(token);
        if (fresh !== null) setGarden(fresh);
        setRebuilt((n) => n + 1);
        setStatus('Schatten berechnet.');
      } finally {
        setRebuilding(false);
      }
    });
  }, [client, token, run, setLightMap, setGarden, setStatus]);

  return { mapMonth, changeMonth, monthLoading, rebuild, rebuilding, rebuilt };
}
