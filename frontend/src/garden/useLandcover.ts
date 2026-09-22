import { useCallback, useEffect, useRef, useState } from 'react';

import type { Landcover, NinaNaturClient } from '../api/client';

/** When an empty landcover is asked for again (doc 114). */
export const LANDCOVER_RETRY_MS = [5_000, 20_000, 60_000];

/**
 * The land around the garden (doc 114), outside the garden's own fetch: it is
 * decoration, so a slow answer must not hold up "geladen" and a failed one must
 * not say "Laden fehlgeschlagen" about a garden that loaded.
 *
 * The server fetches it after answering — a new garden, a shade rebuild — so
 * an empty answer is asked again a few times, further apart each time, and
 * `reloadLandcover` starts over after a rebuild, which is where an older garden
 * first gets it.
 */
export function useLandcover(client: NinaNaturClient, token: string) {
  const [landcover, setLandcover] = useState<Landcover | null>(null);
  const [asked, setAsked] = useState(0);
  const tries = useRef({ token, tries: 0 });
  const reloadLandcover = useCallback(() => {
    tries.current.tries = 0;
    setAsked((n) => n + 1);
  }, []);
  useEffect(() => {
    let current = true;
    let again: ReturnType<typeof setTimeout> | undefined;
    if (tries.current.token !== token) tries.current = { token, tries: 0 };
    client.landcover(token)
      .then((found) => {
        if (!current) return;
        setLandcover(found);
        const wait = LANDCOVER_RETRY_MS[tries.current.tries];
        if ((found?.areas.length ?? 0) > 0 || wait === undefined) return;
        tries.current.tries += 1;
        again = setTimeout(() => setAsked((n) => n + 1), wait);
      })
      .catch((error: unknown) => console.warn('Umgebung der Karte nicht geladen', error));
    return () => {
      current = false;
      if (again !== undefined) clearTimeout(again);
    };
  }, [client, token, asked]);
  return { landcover, reloadLandcover };
}
