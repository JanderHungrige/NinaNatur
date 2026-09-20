import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { Point } from '../canvas/viewport';
import { draftSketch } from './draft-sketch';
import type { DecoratedShape } from './types';

/* What his style has not drawn, drawn in his hand (doc 98). */

const box = (x: number, y: number, w: number, d: number): Point[] => [
  { x: x - w / 2, y: y - d / 2 }, { x: x + w / 2, y: y - d / 2 },
  { x: x + w / 2, y: y + d / 2 }, { x: x - w / 2, y: y + d / 2 },
];

function shape(kind: string, symbol: string, points: Point[], extra: Partial<DecoratedShape> = {},
): DecoratedShape {
  return { key: `obstacle-${kind}`, kind, symbol, ground: false, points, line: null, raised: 0,
           roofLines: [], roof: 'unknown', ...extra };
}

/** What the theme draws for one shape, near, at 5 cm a pixel. */
function drawn(s: DecoratedShape) {
  const { under, over } = draftSketch.decorate!(s, 'near', 0.05);
  const { container } = render(<svg><g className="under">{under}</g><g className="over">{over}</g></svg>);
  return {
    marks: (mark: string) => container.querySelectorAll(`[data-mark="${mark}"]`),
    under: container.querySelector('g.under')!,
  };
}

describe('roofs', () => {
  const gable = shape('house', 'building', box(0, 0, 10, 6),
    { roofLines: [[{ x: -5, y: 0 }, { x: 5, y: 0 }]] });

  it('are drawn from the lines the server gives', () => {
    const roof = drawn(gable).marks('roof');
    expect(roof).toHaveLength(1);
    // The ridge runs the house's length: its path starts at one gable end.
    expect(roof[0]!.getAttribute('d')).toMatch(/^M-5,/);
  });

  it('points a pent roof down its fall, from the upper edge the server gives', () => {
    const pent = shape('house', 'building', box(0, 0, 5, 4),
      { roof: 'pent', roofLines: [[{ x: -2.5, y: 2 }, { x: 2.5, y: 2 }]] });
    const d = drawn(pent).marks('roof')[0]!.getAttribute('d')!;
    // The edge, then the arrow's shaft and its two barbs: four strokes.
    expect(d.match(/M/g)).toHaveLength(4);
  });

  it('and not at all where the model has a plane', () => {
    expect(drawn({ ...gable, roofLines: [] }).marks('roof')).toHaveLength(0);
  });
});

describe('raised beds', () => {
  const flat = shape('bed', 'planting', box(0, 0, 3, 1.5));

  it('carry a second edge inside the first, and a shadow beneath', () => {
    const raised = drawn({ ...flat, raised: 0.5 });
    expect(raised.marks('inner')).toHaveLength(1);
    expect(raised.under.querySelectorAll('[data-mark="shadow"]')).toHaveLength(1);
  });

  it('where a bed on the ground has neither', () => {
    const ground = drawn(flat);
    expect(ground.marks('inner')).toHaveLength(0);
    expect(ground.marks('shadow')).toHaveLength(0);
  });
});

describe('hedges and shrubs', () => {
  it('hatches a hedge along its shaded side, and a lawn not at all', () => {
    expect(drawn(shape('hedge', 'foliage', box(0, 0, 8, 0.8))).marks('ticks')).toHaveLength(1);
    expect(drawn(shape('lawn', 'grass', box(0, 0, 8, 0.8))).marks('ticks')).toHaveLength(0);
  });

  it('gives a shrub his Tree 2 and a tree his Tree 1', () => {
    expect(draftSketch.fill('crown', 'near', 'shrub')).toBe('url(#ds-shrub-near)');
    expect(draftSketch.fill('crown', 'mid', 'tree')).toBe('url(#ds-tree-mid)');
    // His rings inside the crown: three inks where Tree 1 has two.
    const crown = Array.from({ length: 12 }, (_, i) => ({
      x: 3 * Math.cos((i / 12) * 2 * Math.PI), y: 3 * Math.sin((i / 12) * 2 * Math.PI) }));
    expect(drawn(shape('shrub', 'crown', crown)).marks('ink')).toHaveLength(3);
    expect(drawn(shape('tree', 'crown', crown)).marks('ink')).toHaveLength(2);
  });
});

describe('fences and walls, in his line', () => {
  const fence = shape('fence', 'fence', box(0, 0, 0.1, 14.5),
    { line: [{ x: 0, y: -7.25 }, { x: 0, y: 7.25 }] });

  it('sets a fence post every 3.2 m along its line, and draws no outline round it', () => {
    const along = drawn(fence);
    const posts = along.marks('line-boxes');
    expect(posts).toHaveLength(1);
    expect(posts[0]!.getAttribute('d')!.match(/M/g)).toHaveLength(5);
    expect(along.marks('line-ink')).toHaveLength(1);
    expect(along.marks('ink')).toHaveLength(0);
    // Close enough to see them, his pictures of the posts are drawn over the squares.
    expect(along.marks('line-marks')).toHaveLength(1);
  });

  it('fits a wall into its own outline: clipped to it, his faces its edges', () => {
    const wall = drawn(shape('wall', 'masonry', box(0, 0, 8, 0.3)));
    const fitted = wall.marks('fitted');
    expect(fitted).toHaveLength(1);
    expect(fitted[0]!.querySelector('clipPath path')).not.toBeNull();
    // Of his four strokes, the two faces are the wall's own outline; his two
    // bands down the middle are what is left to draw.
    expect(wall.marks('line-ink')).toHaveLength(2);
    expect(wall.marks('ink').length).toBeGreaterThan(0);
  });
});

describe('streets, which arrive as ways and meet at junctions', () => {
  // A T: a road across, and one joining it from the south.
  const across = shape('street', 'paving', box(0, 0, 36, 6),
    { line: [{ x: -18, y: 0 }, { x: 18, y: 0 }] });
  const joining = shape('street', 'paving', box(6, 4, 5, 8),
    { line: [{ x: 6, y: 0 }, { x: 6, y: 8 }] });

  it('draws no outline of its own round a single band', () => {
    expect(drawn(across).marks('ink')).toHaveLength(0);
    expect(drawn(across).marks('line-ink')).toHaveLength(0);
  });

  const Plan = draftSketch.Plan!;

  it('outlines the network once, and shows the line only outside it', () => {
    const { container } = render(<svg><Plan shapes={[across, joining]} metresPerPixel={0.05} /></svg>);
    const ink = container.querySelector('[data-mark="roads"] path[stroke]')!;
    const mask = container.querySelector('mask')!;
    // One line for both bands, and the mask's cut-out is that same line: what
    // lies on a road is hidden, so nothing crosses the junction.
    expect(ink.getAttribute('d')).toBe(mask.querySelector('path')!.getAttribute('d'));
    expect(ink.getAttribute('mask')).toBe(`url(#${mask.getAttribute('id')})`);
    expect(mask.querySelector('rect')!.getAttribute('fill')).toBe('#ffffff');
    expect(mask.querySelector('path')!.getAttribute('fill')).toBe('#000000');
  });

  it('and draws nothing at all where a garden has no street', () => {
    const { container } = render(<svg><Plan shapes={[]} metresPerPixel={0.05} /></svg>);
    expect(container.querySelector('[data-mark="roads"]')).toBeNull();
  });
});
