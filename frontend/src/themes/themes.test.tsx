import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { Viewport } from '../canvas/viewport';
import { CanvasScene } from '../components/CanvasScene';
import { SHEET_GARDENS } from '../sheet/gardens';
import { PlanThemeProvider } from './context';
import { THEMES, themeById } from './index';
import { technisch } from './technisch';
import type { LevelOfDetail, PlanTheme } from './types';

/* The plan's look has one seam (doc 96): a theme gives the defs, the fills and
   the one filter, and nothing else in the scene decides them. */

const small = SHEET_GARDENS[0]!.garden;
const view: Viewport = { centreX: 0, centreY: 2, spanM: 40, widthPx: 400, heightPx: 300 };
const nothing = (): void => undefined;

function scene(theme?: PlanTheme, at: Viewport = view) {
  const plan = (
    <svg>
      <CanvasScene garden={small} view={at} spacing={1} selectedBedId={null} draft={[]}
                   onSelectBed={nothing} />
    </svg>
  );
  return render(theme === undefined ? plan : <PlanThemeProvider theme={theme}>{plan}</PlanThemeProvider>);
}

const probe = (overrides: Partial<PlanTheme> = {}): PlanTheme => ({
  id: 'probe',
  label: 'Probe',
  provenance: 'NinaNatur',
  Defs: () => <pattern id="probe-wash" />,
  fill: (symbol) => `url(#probe-${symbol})`,
  bedFill: () => 'url(#probe-bed)',
  objectsFilter: 'url(#probe-filter)',
  lodAt: () => 'near',
  ...overrides,
});

describe('the plan theme (doc 96)', () => {
  it('is Technisch unless somebody says otherwise', () => {
    const { container } = scene();
    expect(container.querySelector('.plan-theme--technisch')).not.toBeNull();
    expect(container.querySelector('#watercolour')).not.toBeNull();
    expect(container.querySelector('g.canvas__objects')?.getAttribute('filter')).toBe('url(#watercolour)');
    expect(container.querySelector('polygon.obstacle--lawn')?.getAttribute('fill')).toBe('url(#symbol-grass)');
    // A bed is painted by the stylesheet in Technisch, as it always was.
    expect(container.querySelector('polygon.bed')?.hasAttribute('fill')).toBe(false);
  });

  it('is the only thing the shapes take their fill and their filter from', () => {
    const { container } = scene(probe());
    const shapes = container.querySelectorAll('polygon.obstacle, polygon.bed');
    expect(shapes.length).toBe(small.obstacles.length + small.beds.length);
    for (const shape of shapes) expect(shape.getAttribute('fill')).toMatch(/^url\(#probe-/);
    expect(container.querySelector('g.canvas__objects')?.getAttribute('filter')).toBe('url(#probe-filter)');
    expect(container.querySelector('#probe-wash')).not.toBeNull();
    expect(container.querySelector('#watercolour')).toBeNull();
    expect(container.querySelector('.plan-theme--probe')).not.toBeNull();
  });

  it('may leave the shapes unfiltered', () => {
    const { container } = scene(probe({ objectsFilter: null }));
    expect(container.querySelector('g.canvas__objects')?.hasAttribute('filter')).toBe(false);
  });

  it('filters nothing but the shapes: what can be touched is where it is drawn', () => {
    const { container } = scene(probe());
    const filtered = [...container.querySelectorAll('[filter]')];
    expect(filtered.map((node) => node.getAttribute('class'))).toEqual(['canvas__objects']);
  });

  it('draws at the level of detail the scale asks for', () => {
    const asked: LevelOfDetail[] = [];
    const theme = probe({
      lodAt: (metresPerPixel) => (metresPerPixel > 0.2 ? 'far' : 'near'),
      fill: (symbol, lod) => {
        asked.push(lod);
        return `url(#probe-${symbol})`;
      },
    });
    scene(theme, { ...view, spanM: 120 });
    expect(new Set(asked)).toEqual(new Set(['far']));
    asked.length = 0;
    scene(theme, { ...view, spanM: 12 });
    expect(new Set(asked)).toEqual(new Set(['near']));
  });

  it('asks for each shape at the size that shape is drawn (doc 99)', () => {
    // Every shape on one plan, at one scale, and a theme that answers by size:
    // what the scene must pass is the shape's own width in metres.
    const sizes: (number | undefined)[] = [];
    const theme = probe({
      lodAt: (_mpp, acrossM) => {
        sizes.push(acrossM);
        return acrossM !== undefined && acrossM < 2 ? 'far' : 'near';
      },
      fill: (symbol, lod) => `url(#probe-${symbol}-${lod})`,
    });
    const { container } = scene(theme);
    expect(sizes.some((across) => across !== undefined)).toBe(true);
    // A garden of one size everywhere would prove nothing: these differ.
    const drawn = [...container.querySelectorAll('polygon.obstacle')]
      .map((shape) => shape.getAttribute('fill') ?? '');
    expect(drawn.some((fill) => fill.endsWith('-near)'))).toBe(true);
    expect(drawn.some((fill) => fill.endsWith('-far)'))).toBe(true);
  });

  it('draws the sheet the theme says it is on, under the grid (doc 99)', () => {
    const { container } = scene(probe({ paper: 'url(#probe-paper)' }));
    const paper = container.querySelector('rect.canvas__paper')!;
    expect(paper.getAttribute('fill')).toBe('url(#probe-paper)');
    // Under the grid, because the grid is drawn on the paper — and under the
    // shapes, which stand on it.
    const grid = container.querySelector('rect[fill="url(#grid)"]')!;
    expect(paper.compareDocumentPosition(grid) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(paper.getAttribute('aria-hidden')).toBe('true');
  });

  it('and draws no sheet at all for a theme that is drawn on the page itself', () => {
    expect(scene(probe()).container.querySelector('rect.canvas__paper')).toBeNull();
    expect(scene(technisch).container.querySelector('rect.canvas__paper')).toBeNull();
  });

  it('is found by its id, and an id nobody knows is Technisch', () => {
    expect(themeById('technisch')).toBe(technisch);
    expect(themeById('verschollen')).toBe(technisch);
    expect(THEMES.map((t) => t.id)).toContain('technisch');
  });
});
