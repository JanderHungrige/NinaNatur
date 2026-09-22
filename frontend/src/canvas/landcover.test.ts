import { describe, expect, it } from 'vitest';

import type { Landcover } from '../api/client';
import { shed } from '../testing/gardens';
import { landPaths, outsidePlots, plotsOf, ringPath, signedArea } from './landcover';

/* The land around a garden as paths (doc 114). */

const square = (x0: number, y0: number, x1: number, y1: number) =>
  [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];

function land(...areas: Landcover['areas']): Landcover {
  return { areas, attribution: '© OpenStreetMap-Mitwirkende', licence: 'ODbL-1.0' };
}

describe('the land as paths', () => {
  it('draws a ring in the plan’s own axes, north up', () => {
    expect(ringPath([[1, 2], [3, 2], [3, 5]])).toBe('M1 -2L3 -2L3 -5Z');
  });

  it('knows which way round a ring runs', () => {
    expect(signedArea(square(0, 0, 10, 10))).toBe(100);
    expect(signedArea([...square(0, 0, 10, 10)].reverse())).toBe(-100);
  });

  it('is one path per class, however many areas it has', () => {
    const paths = landPaths(land(
      { kind: 'wood', rings: [square(0, 0, 10, 10)] },
      { kind: 'wood', rings: [square(20, 0, 30, 10)] },
      { kind: 'water', rings: [square(40, 0, 45, 5)] },
    ));
    expect(paths.map((p) => p.kind)).toEqual(['wood', 'water']);
    expect(paths[0]?.d.match(/M/g)).toHaveLength(2);
  });

  it('puts the class of the largest area behind the rest', () => {
    // A residential quarter, with a park in it: the park is drawn over it.
    const paths = landPaths(land(
      { kind: 'grass', rings: [square(10, 10, 30, 30)] },
      { kind: 'residential', rings: [square(-100, -100, 100, 100)] },
    ));
    expect(paths.map((p) => p.kind)).toEqual(['residential', 'grass']);
  });

  it('keeps a hole as a ring of its own in its class’s path', () => {
    const hole = [...square(-5, -5, 5, 5)].reverse();
    const [wood] = landPaths(land({ kind: 'wood', rings: [square(-50, -50, 50, 50), hole] }));
    expect(wood?.d.match(/Z/g)).toHaveLength(2);
  });
});

describe('the plot, cut out of the land', () => {
  const plot = shed({ kind: 'garden', footprint: square(-10, -10, 10, 10) });

  it('is the garden’s own ground, and nothing else', () => {
    expect(plotsOf([shed(), plot])).toEqual([square(-10, -10, 10, 10)]);
  });

  it('is a frame round the land with the plot inside it, for an even-odd clip', () => {
    const clip = outsidePlots(land({ kind: 'wood', rings: [square(-50, -40, 60, 70)] }), [plot.footprint]);
    // The frame first, a metre past the land on every side; then the plot.
    expect(clip).toBe(`${ringPath([[-51, -41], [61, -41], [61, 71], [-51, 71]])}${ringPath(plot.footprint)}`);
  });

  it('is nothing to cut for a garden without a plot', () => {
    expect(outsidePlots(land({ kind: 'wood', rings: [square(0, 0, 9, 9)] }), [])).toBeNull();
  });
});
