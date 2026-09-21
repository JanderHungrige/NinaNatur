import type { PlanTheme } from '../types';
import { TechnischSymbols } from './symbols';

/**
 * The plan as it was drawn until Wave 24 (doc 96), and what it falls back to —
 * with one change since: the garden's own ground is washed in grass
 * (2026-09-21). Doc 95's record holds its pixels.
 */
export const technisch: PlanTheme = {
  id: 'technisch',
  label: 'Technisch',
  provenance: 'NinaNatur',
  Defs: TechnischSymbols,
  fill: (symbol) => `url(#symbol-${symbol})`,
  // A bed is painted by the stylesheet (`.bed`), as it always was: the planting
  // wash exists, but has never been what a bed shows.
  bedFill: () => undefined,
  objectsFilter: 'url(#watercolour)',
  lodAt: () => 'near',
};
