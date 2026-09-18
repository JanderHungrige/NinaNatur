import { type ReactNode, createContext, useContext } from 'react';

import { technisch } from './technisch';
import type { PlanTheme } from './types';

/* Which theme the plan is drawn in (doc 96). Technisch unless somebody says otherwise. */

const PlanThemeContext = createContext<PlanTheme>(technisch);

export function PlanThemeProvider({ theme, children }: { theme: PlanTheme; children: ReactNode }) {
  return <PlanThemeContext.Provider value={theme}>{children}</PlanThemeContext.Provider>;
}

export function usePlanTheme(): PlanTheme {
  return useContext(PlanThemeContext);
}
