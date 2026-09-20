import { useCallback, useEffect, useMemo, useState } from 'react';

import { asksForContrast, chosenTheme, offered, remember, remembered } from './choice';
import { loadTheme, preloaded } from './index';
import type { ThemeOnOffer } from './index';
import { technisch } from './technisch';
import type { PlanTheme } from './types';

export interface PlanChoice {
  /** The theme the plan is drawn in, once its chunk and images have arrived. */
  theme: PlanTheme;
  /** What is on offer here, for the picker (doc 100). */
  options: readonly ThemeOnOffer[];
  /** The id that was chosen — which is not the drawn one until it has loaded. */
  chosen: string;
  choose: (id: string) => void;
  /** High contrast has taken the choice away. */
  overridden: boolean;
}

/**
 * Which style this page draws its plan in (docs 97, 100): what the viewer chose
 * and their browser remembered, or what the address asks for — and Technisch
 * whatever they chose, where more contrast was asked for. A theme that fails to
 * load leaves the plan as it was.
 */
export function usePageTheme(): PlanChoice {
  const [theme, setTheme] = useState<PlanTheme>(technisch);
  const overridden = useMemo(asksForContrast, []);
  const [chosen, setChosen] = useState(technisch.id);

  useEffect(() => {
    setChosen(chosenTheme({
      search: window.location.search,
      stored: remembered(),
      moreContrast: overridden,
    }));
  }, [overridden]);

  useEffect(() => {
    if (chosen === technisch.id) {
      setTheme(technisch);
      return undefined;
    }
    let current = true;
    loadTheme(chosen)
      .then(preloaded)
      .then((loaded) => {
        if (current) setTheme(loaded);
      })
      .catch(() => undefined);
    return () => {
      current = false;
    };
  }, [chosen]);

  const choose = useCallback((id: string) => {
    remember(id);
    setChosen(id);
  }, []);

  return { theme, options: offered(), chosen, choose, overridden };
}
