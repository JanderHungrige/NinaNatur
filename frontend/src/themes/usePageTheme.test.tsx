import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { fakeClient, openWorkspace, resetApp, stubMatchMedia } from '../testing/appFixtures';
import { usePageTheme } from './usePageTheme';

/* Which style the page draws in, from its first drawing (docs 97, 100). Draft
   Sketch is the default since 2026-09-28; chosen in an effect and fetched as a
   chunk, every load drew the plan and its buttons in Technisch first and then
   changed style under the gardener's eyes. */

beforeEach(() => {
  try {
    window.localStorage.clear();
  } catch {
    // A browser that refuses storage chooses the default.
  }
});
afterEach(() => {
  vi.unstubAllGlobals();
  resetApp();
});

function firstDrawn(): string[] {
  const drawn: string[] = [];
  renderHook(() => {
    const choice = usePageTheme();
    drawn.push(choice.theme.id);
    return choice;
  });
  return drawn;
}

describe('usePageTheme', () => {
  it('draws Draft Sketch from the very first drawing where nobody has chosen', () => {
    stubMatchMedia();
    expect(firstDrawn()).toEqual(['draft-sketch']);
  });

  it('draws Technisch from the first drawing where more contrast is asked for', () => {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: query === '(prefers-contrast: more)', media: query, onchange: null,
      addListener: vi.fn(), removeListener: vi.fn(), addEventListener: vi.fn(),
      removeEventListener: vi.fn(), dispatchEvent: vi.fn(),
    }));
    expect(firstDrawn()).toEqual(['technisch']);
  });
});

describe('the page\'s controls follow the style drawn', () => {
  it('name it on the app, where his buttons are keyed', async () => {
    stubMatchMedia();
    await openWorkspace(fakeClient());
    expect(document.querySelector('.app')?.getAttribute('data-plan-theme')).toBe('draft-sketch');
  });
});
