import { technisch } from './technisch';
import type { PlanTheme } from './types';

/** Every theme the plan can be drawn in, the fallback first (doc 96). */
export const THEMES: readonly PlanTheme[] = [technisch];

/** The theme with this id; one nobody knows — renamed, withdrawn — is Technisch. */
export function themeById(id: string | null | undefined): PlanTheme {
  return THEMES.find((theme) => theme.id === id) ?? technisch;
}

export type { LevelOfDetail, PlanTheme } from './types';
