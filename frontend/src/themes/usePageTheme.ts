import { useCallback, useEffect, useMemo, useState } from 'react';

import { asksForContrast, chosenTheme, offered, remember, remembered } from './choice';
import { preloaded, themeById } from './index';
import type { ThemeOnOffer } from './index';
import type { PlanTheme } from './types';

export interface PlanChoice {
  /** The theme the plan is drawn in: the chosen one, from the first drawing. */
  theme: PlanTheme;
  /** What is on offer here, for the picker (doc 100). */
  options: readonly ThemeOnOffer[];
  /** The id that was chosen. */
  chosen: string;
  choose: (id: string) => void;
  /** High contrast has taken the choice away. */
  overridden: boolean;
}

/**
 * Which style this page draws its plan in (docs 97, 100): what the viewer chose
 * and their browser remembered, or what the address asks for — Draft Sketch
 * where nobody has said — and Technisch whatever they chose, where more
 * contrast was asked for.
 */
export function usePageTheme(): PlanChoice {
  const overridden = useMemo(asksForContrast, []);
  // Chosen before the first drawing, not after it: an effect drew one plan
  // in Technisch and then the chosen style over it (2026-09-28).
  const [chosen, setChosen] = useState(() => chosenTheme({
    search: window.location.search,
    stored: remembered(),
    moreContrast: overridden,
  }));
  const theme = themeById(chosen);

  // The images the style draws with, fetched now: the plan is drawn at once
  // and its washes fill in as they arrive, rather than waiting in another style.
  useEffect(() => {
    void preloaded(theme);
  }, [theme]);

  const choose = useCallback((id: string) => {
    remember(id);
    setChosen(id);
  }, []);

  return { theme, options: offered(), chosen, choose, overridden };
}
