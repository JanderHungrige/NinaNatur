import { useEffect, useState } from 'react';

import { loadTheme, preloaded, themeFor } from './index';
import { technisch } from './technisch';
import type { PlanTheme } from './types';

/**
 * The theme this page draws its plan in (doc 97): Technisch, unless this is the
 * preview and another is asked for by name — and then from the moment its
 * chunk and its images have arrived. A theme that fails to load leaves the plan
 * as it was.
 */
export function usePageTheme(environment: string | null): PlanTheme {
  const [theme, setTheme] = useState<PlanTheme>(technisch);
  useEffect(() => {
    const id = themeFor(environment, window.location.search);
    if (id === technisch.id) return undefined;
    let current = true;
    loadTheme(id)
      .then(preloaded)
      .then((loaded) => {
        if (current) setTheme(loaded);
      })
      .catch(() => undefined);
    return () => {
      current = false;
    };
  }, [environment]);
  return theme;
}
