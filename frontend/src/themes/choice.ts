/**
 * Which style the plan is drawn in, and who decides (doc 100).
 *
 * The viewer's own choice, remembered in their browser; the address, which the
 * contact sheet and every probe use; and what the deployment actually serves —
 * with high contrast able to take the choice away from all three, because a
 * style made of washes and pencil is the wrong answer to "make this clearer".
 *
 * A preference, never data: it lives in the browser, so two people looking at
 * one shared garden each see it in their own hand.
 */
import { ON_OFFER, type ThemeOnOffer, themeById } from './index';
import { technisch } from './technisch';

export const STORAGE_KEY = 'ninanatur.plan-theme';
/** Drawn only where its files are served (doc 97). */
const PREVIEW_ONLY = 'draft-sketch';
const PREVIEW = 'dev';

export interface Circumstances {
  environment: string | null;
  search: string;
  /** What the browser remembered, or null. Passed in so this stays pure. */
  stored: string | null;
  moreContrast: boolean;
}

/** The styles this deployment can actually draw. */
export function offered(environment: string | null): readonly ThemeOnOffer[] {
  return ON_OFFER.filter((theme) => theme.id !== PREVIEW_ONLY || environment === PREVIEW);
}

export function chosenTheme({ environment, search, stored, moreContrast }: Circumstances): string {
  if (moreContrast) return technisch.id;
  const asked = new URLSearchParams(search).get('theme') ?? stored;
  const here = offered(environment);
  const found = here.find((theme) => theme.id === asked);
  return found?.id ?? technisch.id;
}

/** What the browser remembered, or null — including when it refuses to say. */
export function remembered(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

/** Keep it for next time, where the browser allows one. */
export function remember(id: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // A private window remembers nothing, and the choice lasts the page.
  }
}

/** Whether the viewer has asked for more contrast than a drawing can give. */
export function asksForContrast(): boolean {
  if (typeof window.matchMedia !== 'function') return false;
  return ['(prefers-contrast: more)', '(forced-colors: active)']
    .some((query) => window.matchMedia(query).matches);
}

export { themeById };
