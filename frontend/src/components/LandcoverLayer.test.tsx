import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { Landcover } from '../api/client';
import { shed } from '../testing/gardens';
import { draftSketch } from '../themes/draft-sketch';
import { technisch } from '../themes/technisch';
import type { PlanTheme } from '../themes/types';
import { LandcoverLayer } from './LandcoverLayer';

/* The land around the garden on the plan (doc 114). */

const square = (x0: number, y0: number, x1: number, y1: number) =>
  [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];

const EVERY_CLASS: Landcover = {
  attribution: '© OpenStreetMap-Mitwirkende',
  licence: 'ODbL-1.0',
  areas: [
    { kind: 'residential', rings: [square(-150, -150, 150, 150)] },
    { kind: 'wood', rings: [square(40, 40, 120, 120)] },
    { kind: 'grass', rings: [square(-120, 40, -40, 100)] },
    { kind: 'water', rings: [square(60, 60, 80, 80)] },
    { kind: 'field', rings: [square(-140, -140, -60, -60)] },
    { kind: 'allotments', rings: [square(40, -120, 100, -60)] },
    { kind: 'paved', rings: [square(-30, -60, -10, -40)] },
    { kind: 'built', rings: [square(10, -60, 30, -40)] },
  ],
};
const PLOT = shed({ kind: 'garden', footprint: square(-10, -10, 10, 10) });

function drawn(theme: PlanTheme = technisch, obstacles = [PLOT], landcover = EVERY_CLASS) {
  const { container } = render(
    <svg><LandcoverLayer landcover={landcover} obstacles={obstacles} theme={theme} scale={0.05} /></svg>,
  );
  return container;
}

const area = (root: Element, kind: string) => root.querySelector(`.landcover__area--${kind}`);

describe('LandcoverLayer', () => {
  it('draws one path per class, filled by the nonzero rule', () => {
    const paths = drawn().querySelectorAll('.landcover__area');
    expect(paths).toHaveLength(8);
    for (const path of paths) expect(path.getAttribute('fill-rule')).toBe('nonzero');
  });

  it('paints each class with the theme’s own symbol where one fits', () => {
    const plan = drawn();
    expect(area(plan, 'grass')?.getAttribute('fill')).toBe('url(#symbol-grass)');
    expect(area(plan, 'wood')?.getAttribute('fill')).toBe('url(#symbol-foliage)');
    expect(area(plan, 'water')?.getAttribute('fill')).toBe('url(#symbol-water)');
    expect(area(plan, 'paved')?.getAttribute('fill')).toBe('url(#symbol-tarmac)');
    expect(area(plan, 'built')?.getAttribute('fill')).toBe('url(#symbol-tarmac)');
    expect(area(plan, 'allotments')?.getAttribute('fill')).toBe('url(#symbol-planting)');
    // Fields and houses have no symbol: the stylesheet washes them.
    expect(area(plan, 'field')?.hasAttribute('fill')).toBe(false);
    expect(area(plan, 'residential')?.hasAttribute('fill')).toBe(false);
  });

  it('is painted in his hand under Draft Sketch', () => {
    expect(area(drawn(draftSketch), 'grass')?.getAttribute('fill')).toBe('url(#ds-grass)');
  });

  it('puts the largest class behind the others', () => {
    const kinds = [...drawn().querySelectorAll('.landcover__area')]
      .map((p) => p.getAttribute('class')?.split('--')[1]);
    expect(kinds[0]).toBe('residential');
    expect(kinds.indexOf('water')).toBeGreaterThan(kinds.indexOf('wood'));
  });

  it('cuts the plot out of every class, so no colour tints the garden', () => {
    const plan = drawn();
    const group = plan.querySelector('[data-testid="landcover"]');
    const id = group?.getAttribute('clip-path')?.match(/^url\(#(.+)\)$/)?.[1];
    expect(id).toBeDefined();
    const clip = plan.querySelector(`clipPath[id="${id}"] path`);
    expect(clip?.getAttribute('clip-rule')).toBe('evenodd');
    // The frame round the land, then the plot's own outline.
    expect(clip?.getAttribute('d')?.endsWith('M-10 10L10 10L10 -10L-10 -10Z')).toBe(true);
  });

  it('cuts nothing out of a garden drawn without a plot', () => {
    const plan = drawn(technisch, [shed()]);
    expect(plan.querySelector('clipPath')).toBeNull();
    expect(plan.querySelector('[data-testid="landcover"]')?.hasAttribute('clip-path')).toBe(false);
  });

  it('is context: never read out, never pointed at', () => {
    const group = drawn().querySelector('[data-testid="landcover"]');
    expect(group?.getAttribute('aria-hidden')).toBe('true');
    expect(group?.getAttribute('class')).toBe('landcover');
  });

  it('draws nothing where nothing is mapped', () => {
    const plan = drawn(technisch, [PLOT], { ...EVERY_CLASS, areas: [] });
    expect(plan.querySelector('[data-testid="landcover"]')).toBeNull();
    expect(plan.querySelector('clipPath')).toBeNull();
  });
});
