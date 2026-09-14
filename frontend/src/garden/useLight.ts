import { useCallback, useEffect, useState } from 'react';

import type { LightMap, NinaNaturClient, ShadowDay, SightlinesOut } from '../api/client';
import type { MapMode } from '../components/SunMap';
import type { Status } from '../useStatus';

/**
 * Light over one garden: the sun map and what it shows, the day being watched,
 * and what is visible from where somebody stands (doc 87).
 */
export function useLight(
  client: NinaNaturClient,
  token: string,
  status: Status,
  setLightMap: (map: LightMap | null) => void,
  floweringMonth: number | null,
) {
  const { run } = status;
  const [shadeOn, setShadeOn] = useState(false);
  const [mapMode, setMapMode] = useState<MapMode>('hours');
  // Null is the whole season, which is the number a plant is placed by.
  const [mapMonth, setMapMonth] = useState<number | null>(null);
  /** A day's shadows, and which frame is showing. Fetched only when the day is
   *  actually being watched — it is a request nobody asks for by opening a
   *  garden. */
  const [day, setDay] = useState<ShadowDay | null>(null);
  const [frame, setFrame] = useState(0);
  const [sightlines, setSightlines] = useState<SightlinesOut | null>(null);
  const [viewpoint, setViewpoint] = useState<{ x: number; y: number } | null>(null);

  /**
   * The day's shadows, fetched when somebody actually wants to watch them.
   *
   * The month follows the filter, so switching months while watching moves the
   * shadows rather than needing a second control. `mapMode === 'day'` is the
   * whole gate: the two heat maps are read, not watched.
   */
  useEffect(() => {
    if (!shadeOn || mapMode !== 'day') {
      setDay(null);
      return;
    }
    const month = floweringMonth ?? 6;
    let dropped = false;
    void client
      .shadowDay(token, month)
      .then((fetched) => {
        if (dropped) return;
        setDay(fetched);
        setFrame(0);
      })
      .catch(() => {
        if (!dropped) setDay(null);
      });
    return () => {
      // A month switched twice in a second must not have the first answer
      // arrive last and win.
      dropped = true;
    };
  }, [client, token, shadeOn, mapMode, floweringMonth]);

  const toggleShade = useCallback((next: boolean) => {
    setShadeOn(next);
    // Leaving the map also leaves the day: the two are one question, and a day
    // playing behind a hidden map is a timer nobody can see.
    if (!next) setDay(null);
  }, []);

  const changeMonth = useCallback(
    (next: number | null) => {
      setMapMonth(next);
      void run('Zeitraum gewechselt', async () => {
        setLightMap(await client.lightMap(token, next));
      });
    },
    [client, token, run, setLightMap],
  );

  const rebuild = useCallback(
    () =>
      void run('Schatten neu berechnen', async () => {
        // The button computes and stores the season. Coming back to a month
        // view afterwards would show a figure the button did not produce.
        setMapMonth(null);
        setLightMap(await client.rebuildLightMap(token));
      }),
    [client, token, run, setLightMap],
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
    toggleShade,
    mapMode,
    setMapMode,
    mapMonth,
    changeMonth,
    rebuild,
    day,
    frame,
    setFrame,
    sightlines,
    viewpoint,
    lookFrom,
    clearSightlines,
  };
}

export type Light = ReturnType<typeof useLight>;
