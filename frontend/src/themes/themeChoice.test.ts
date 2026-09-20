import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { chosenTheme, offered, remember } from './choice';
import { technisch } from './technisch';

/* Which style the plan is drawn in, and who decides (doc 100). */

const DRAFT = 'draft-sketch';
const plain = { search: '', stored: null, moreContrast: false };

beforeEach(() => {
  try {
    window.localStorage.clear();
  } catch {
    // A browser that refuses storage is the test's other case.
  }
});
afterEach(() => vi.unstubAllGlobals());

describe('what is on offer', () => {
  it('is every style, wherever the app runs', () => {
    // His files were the preview's alone until he had seen the plan in his
    // hand; the owner lifted that on 2026-09-20 (docs 97, 100).
    expect(offered().map((t) => t.id)).toEqual([technisch.id, DRAFT]);
  });
});

describe('which one is drawn', () => {
  it('is Technisch until somebody says otherwise', () => {
    expect(chosenTheme(plain)).toBe(technisch.id);
  });

  it('is what the viewer chose before, in their own browser', () => {
    expect(chosenTheme({ ...plain, stored: DRAFT })).toBe(DRAFT);
  });

  it('or what the address asks for — which is what the sheet and the probes use', () => {
    expect(chosenTheme({ ...plain, search: `?theme=${DRAFT}` })).toBe(DRAFT);
  });

  it('and never a style nobody has heard of', () => {
    expect(chosenTheme({ ...plain, stored: 'verschollen' })).toBe(technisch.id);
  });

  it('is Technisch when the viewer asks for more contrast, whatever they chose', () => {
    // His style is washes, grain and pencil: the wrong answer to "make this
    // clearer". Doc 98 used to hide the ink, which left a drawing with none of
    // its marks.
    expect(chosenTheme({ ...plain, stored: DRAFT, moreContrast: true })).toBe(technisch.id);
  });
});

describe('remembering it', () => {
  it('keeps the choice for next time', () => {
    remember(DRAFT);
    expect(window.localStorage.getItem('ninanatur.plan-theme')).toBe(DRAFT);
  });

  it('and a browser that refuses storage loses nothing but the memory', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => { throw new Error('denied'); },
      setItem: () => { throw new Error('denied'); },
    });
    expect(() => remember(DRAFT)).not.toThrow();
    expect(chosenTheme(plain)).toBe(technisch.id);
  });
});
