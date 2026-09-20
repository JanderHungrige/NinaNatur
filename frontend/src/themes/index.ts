import { technisch } from './technisch';
import type { PlanTheme } from './types';

/** Every theme the plan can be drawn in, the fallback first (doc 96). */
export const THEMES: readonly PlanTheme[] = [technisch];

/** The theme with this id; one nobody knows — renamed, withdrawn — is Technisch. */
export function themeById(id: string | null | undefined): PlanTheme {
  return THEMES.find((theme) => theme.id === id) ?? technisch;
}

/** Draft Sketch: a chunk of its own, so it is named here rather than held in
 *  THEMES, which would pull it into every page (docs 97, 100). */
const DRAFT_SKETCH = 'draft-sketch';

/** A style the picker can name without loading it (doc 100). A chunk of its own
 *  is the point of the lazy theme, so its label is repeated here — and
 *  `themes.test.tsx` fails if the two ever disagree. */
export interface ThemeOnOffer {
  id: string;
  label: string;
}

/** Every style that exists, whether or not this deployment serves it. */
export const ON_OFFER: readonly ThemeOnOffer[] = [
  ...THEMES.map((theme) => ({ id: theme.id, label: theme.label })),
  { id: DRAFT_SKETCH, label: 'Draft Sketch' },
];

/**
 * Which theme this page may draw. Draft Sketch only on the preview, and only
 * when asked for by name: nothing of his is shown in public before he has seen
 * it. Which deployment this is, only the server knows (`/healthz`).
 */
/** The theme with this id. Draft Sketch is a chunk of its own, fetched only
 *  when it is drawn — which production never asks for. */
export async function loadTheme(id: string): Promise<PlanTheme> {
  if (id === DRAFT_SKETCH) return (await import('./draft-sketch')).draftSketch;
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
