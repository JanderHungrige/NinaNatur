import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { Viewport } from '../canvas/viewport';
import { CanvasScene } from '../components/CanvasScene';
import { PlanCredit } from '../components/PlanCredit';
import { KINDS, isGround } from '../kinds';
import { SHEET_GARDENS } from '../sheet/gardens';
import { PlanThemeProvider } from './context';
import { draftSketch } from './draft-sketch';
import { THEMES, loadTheme, themeFor } from './index';
import { technisch } from './technisch';

/* Draft Sketch as a theme of the plan (doc 97). */

const small = SHEET_GARDENS[0]!.garden;
const view: Viewport = { centreX: 0, centreY: 2, spanM: 40, widthPx: 400, heightPx: 300 };
const nothing = (): void => undefined;

function drawn() {
  return render(
    <PlanThemeProvider theme={draftSketch}>
      <svg>
        <CanvasScene garden={small} view={view} spacing={1} selectedBedId={null} draft={[]}
                     onSelectBed={nothing} />
      </svg>
    </PlanThemeProvider>,
  );
}

describe('the Draft Sketch theme', () => {
  it('fills every kind with a pattern its own defs define, the ground excepted', () => {
    const { container } = drawn();
    for (const kind of KINDS) {
      if (isGround(kind.kind)) continue;
      for (const lod of ['near', 'mid', 'far'] as const) {
        const fill = draftSketch.fill(kind.symbol, lod, kind.kind);
        expect(fill, `${kind.kind} at ${lod}`).toMatch(/^url\(#ds-[a-z0-9-]+\)$/);
        const id = fill!.slice(5, -1);
        expect(container.querySelector(`[id="${id}"]`), `${id} is not defined`).not.toBeNull();
      }
    }
  });

  it('takes its levels of detail from his scale ranges, in metres per pixel', () => {
    expect(draftSketch.lodAt(0.1)).toBe('near');
    expect(draftSketch.lodAt(0.5)).toBe('mid');
    expect(draftSketch.lodAt(1)).toBe('far');
  });

  it('draws each shadow right beneath its shape, the ink over them all, and neither is a target', () => {
    const { container } = drawn();
    const layers = [...container.querySelectorAll('g.canvas__objects, g.canvas__ink')];
    expect(layers.map((g) => g.getAttribute('class'))).toEqual(['canvas__objects', 'canvas__ink']);
    const shadows = [...container.querySelectorAll('g.canvas__objects > .canvas__shadow')];
    expect(shadows.length).toBeGreaterThan(0);
    for (const shadow of shadows) {
      // The shape it belongs to comes straight after it, so it falls on what lies beneath.
      expect(shadow.nextElementSibling?.hasAttribute('data-element-id')).toBe(true);
    }
    for (const layer of [...shadows, container.querySelector('g.canvas__ink')!]) {
      expect(layer.getAttribute('pointer-events')).toBe('none');
      expect(layer.getAttribute('aria-hidden')).toBe('true');
    }
    expect(container.querySelectorAll('g.canvas__ink path').length).toBeGreaterThan(0);
  });

  it('refers to nothing it does not define', () => {
    // A tinted mark whose mask is missing is drawn as a hard square of colour.
    const { container } = drawn();
    const ids = new Set([...container.querySelectorAll('[id]')].map((e) => e.id));
    const refs = [...container.querySelectorAll('*')]
      .flatMap((e) => ['fill', 'mask', 'clip-path'].map((name) => e.getAttribute(name) ?? ''))
      .flatMap((value) => [...value.matchAll(/url\(#([^)]+)\)/g)].map((m) => m[1]!));
    expect(refs.length).toBeGreaterThan(0);
    expect(refs.filter((id) => !ids.has(id))).toEqual([]);
  });

  it('filters nothing at all', () => {
    const { container } = drawn();
    expect(container.querySelectorAll('[filter]')).toHaveLength(0);
  });

  it('loads every image as a file, never inline', () => {
    const { container } = drawn();
    const images = [...container.querySelectorAll('image')];
    expect(images.length).toBeGreaterThan(0);
    for (const image of images) expect(image.getAttribute('href') ?? '').not.toMatch(/^data:/);
  });
});

describe('where Draft Sketch can be seen', () => {
  it('only on the preview, and only when asked for by name', () => {
    expect(themeFor('dev', '?theme=draft-sketch')).toBe('draft-sketch');
    expect(themeFor('dev', '')).toBe('technisch');
    expect(themeFor('prod', '?theme=draft-sketch')).toBe('technisch');
    expect(themeFor(null, '?theme=draft-sketch')).toBe('technisch');
  });

  it('is not among the themes a page starts with, and is fetched when it is asked for', async () => {
    expect(THEMES.map((t) => t.id)).toEqual(['technisch']);
    expect(await loadTheme('draft-sketch')).toBe(draftSketch);
    expect((await loadTheme('technisch')).id).toBe('technisch');
  });
});

describe('whose style it is', () => {
  it('is said on the plan in the words he agreed to, and not for a theme of our own', () => {
    const credited = (theme: typeof technisch) => (
      <PlanThemeProvider theme={theme}><PlanCredit /></PlanThemeProvider>
    );
    const { container, rerender } = render(credited(draftSketch));
    expect(container.textContent).toContain(
      'Zeichenstil nach Draft Sketch von Warren Davison, verwendet und angepasst mit seiner Erlaubnis');
    expect(container.textContent).toContain('with assistance from Louis Hill (@NKYmapLAB)');
    rerender(credited(technisch));
    expect(container.textContent).toBe('');
  });
});
