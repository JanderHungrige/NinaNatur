/**
 * Which style the plan is drawn in, and who decides (doc 100).
 *
 * The viewer's own choice, remembered in their browser, or what the address
 * asks for — with high contrast able to take the choice away from both, because
 * a style made of washes and pencil is the wrong answer to "make this clearer".
 *
 * Every style is on offer everywhere since 2026-09-20: his files were served by
 * the preview alone until he had seen the plan in his hand, and the owner
 * lifted that gate once he had (docs 97, 100).
 *
 * A preference, never data: it lives in the browser, so two people looking at
 * one shared garden each see it in their own hand.
 */
import { ON_OFFER, type ThemeOnOffer, themeById } from './index';
import { technisch } from './technisch';

export const STORAGE_KEY = 'ninanatur.plan-theme';

export interface Circumstances {
  search: string;
  /** What the browser remembered, or null. Passed in so this stays pure. */
  stored: string | null;
  moreContrast: boolean;
}

/** The styles that can be drawn. */
export function offered(): readonly ThemeOnOffer[] {
  return ON_OFFER;
}

export function chosenTheme({ search, stored, moreContrast }: Circumstances): string {
  if (moreContrast) return technisch.id;
  const asked = new URLSearchParams(search).get('theme') ?? stored;
  return offered().find((theme) => theme.id === asked)?.id ?? technisch.id;
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
