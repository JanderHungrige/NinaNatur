import { draftSketch } from './draft-sketch';
import { technisch } from './technisch';
import type { PlanTheme } from './types';

/**
 * Every theme the plan can be drawn in, the fallback first (doc 96).
 *
 * Draft Sketch was a chunk of its own, fetched once a page asked for it, so a
 * page that never showed it never downloaded it (docs 97, 100). Since the
 * owner made it the default (2026-09-28) nearly every page does — and as a
 * chunk, every load drew the plan and its buttons in Technisch first and
 * then changed style under the gardener's eyes. 17 KB compressed, it ships
 * with the page now.
 */
export const THEMES: readonly PlanTheme[] = [technisch, draftSketch];

/** The theme with this id; one nobody knows — renamed, withdrawn — is Technisch. */
export function themeById(id: string | null | undefined): PlanTheme {
  return THEMES.find((theme) => theme.id === id) ?? technisch;
}

/** A style the picker can name (doc 100). */
export interface ThemeOnOffer {
  id: string;
  label: string;
}

/** Every style there is, and on offer everywhere since 2026-09-20 (`choice.ts`). */
export const ON_OFFER: readonly ThemeOnOffer[] =
  THEMES.map((theme) => ({ id: theme.id, label: theme.label }));

/** The theme with this id — for the contact sheet, which waits for it. */
export async function loadTheme(id: string): Promise<PlanTheme> {
  return themeById(id);
}

/** The theme, once every image it draws with has arrived and been decoded. An
 *  image that fails is drawn as missing, which is no reason to keep the plan. */
export async function preloaded(theme: PlanTheme): Promise<PlanTheme> {
  await Promise.all((theme.images ?? []).map(async (src) => {
    const image = new Image();
    image.src = src;
    try {
      await image.decode();
    } catch {
      // Drawn without it.
    }
  }));
  return theme;
}

export type {
  DecoratedShape, Decoration, FurnitureProps, LevelOfDetail, PlanProps, PlanTheme,
} from './types';
