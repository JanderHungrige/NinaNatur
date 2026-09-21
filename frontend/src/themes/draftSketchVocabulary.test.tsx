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
           roofLines: [], roof: 'unknown', bandWidth: null, shadow: { x: 0.6, y: 0.3 }, ...extra };
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

  it('keeps the arrow when the upper edge is two walls, in the middle of both', () => {
    // A notch in the upper wall: the server sends both pieces (review, 2026-09-21).
    const pent = shape('house', 'building', box(0, 0, 8, 4), {
      roof: 'pent',
      roofLines: [[{ x: -4, y: 2 }, { x: 2, y: 2 }], [{ x: 3, y: 2 }, { x: 4, y: 2 }]],
    });
    const d = drawn(pent).marks('roof')[0]!.getAttribute('d')!;
    // Two edges, then the shaft and its barbs.
    expect(d.match(/M/g)).toHaveLength(5);
    // The shaft starts a quarter of the way from the whole edge's middle (0, 2)
    // to the house's centre (0, 0): at (0, 1.5), y flipped — straight down the
    // fall, not askew from the longer piece's middle.
    expect(d).toContain('M0,-1.5L0,');
  });

  /** The arrow's shaft as the drawing has it, in plan metres (y back north). */
  const shaft = (d: string, lines: number): [Point, Point] => {
    const moves = d.split('M').filter(Boolean);
    const numbers = (moves[lines] ?? '').match(/-?\d+(?:\.\d+)?/g)!.map(Number);
    return [{ x: numbers[0]!, y: -numbers[1]! }, { x: numbers[2]!, y: -numbers[3]! }];
  };
  const inside = (p: Point, ring: Point[]) => ring.reduce((odd, a, i) => {
    const b = ring[(i + 1) % ring.length]!;
    return (a.y > p.y) !== (b.y > p.y) && p.x < a.x + ((p.y - a.y) * (b.x - a.x)) / (b.y - a.y)
      ? !odd : odd;
  }, false);

  it('starts the arrow on the house when the upper edge steps back, as on an L', () => {
    // What the server sends for this L falling a degree off south (review, 2026-09-21):
    // the chord between the two walls' far ends has its middle over the garden.
    const ell = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 4 }, { x: 4, y: 4 },
                 { x: 4, y: 8 }, { x: 0, y: 8 }];
    const pent = shape('house', 'building', ell, {
      roof: 'pent', roofFall: 181,
      roofLines: [[{ x: 10, y: 4 }, { x: 4, y: 4 }], [{ x: 4, y: 8 }, { x: 0, y: 8 }]],
    });
    const [tail, tip] = shaft(drawn(pent).marks('roof')[0]!.getAttribute('d')!, 2);
    expect(inside(tail, ell)).toBe(true);
    expect(inside(tip, ell)).toBe(true);
  });

  it('points the arrow down the surveyed fall, not at the middle of a leaning house', () => {
    const leaning = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 13, y: 6 }, { x: 3, y: 6 }];
    const pent = shape('house', 'building', leaning, {
      roof: 'pent', roofFall: 180, roofLines: [[{ x: 13, y: 6 }, { x: 3, y: 6 }]],
    });
    const [tail, tip] = shaft(drawn(pent).marks('roof')[0]!.getAttribute('d')!, 1);
    expect(tip.x).toBeCloseTo(tail.x, 2);
    expect(tip.y).toBeLessThan(tail.y);
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

describe('the shadow the sun casts (doc 99)', () => {
  const house = (extra = {}) => shape('house', 'building',
    box(0, 0, 9, 6), { roof: 'gable', ...extra });

  it('falls where the model says, and reaches from the thing to its end', () => {
    // Eight metres east-north-east: what the server sends for a tall thing at
    // the drawing's moment.
    const drawnHouse = drawn(house({ shadow: { x: 8, y: 3 } }));
    const cast = drawnHouse.under.querySelector('[data-mark="shadow"]')!;
    const xs = [...(cast.getAttribute('d') ?? '').matchAll(/(-?\d+(?:\.\d+)?),-?\d/g)]
      .map((m) => Number(m[1]));
    // The house spans -4.5..4.5. Its shadow is the ground it hides all the way
    // over, so the mark starts at the house and ends 8 m east of it — not a
    // copy of the house floating clear of it.
    expect(Math.min(...xs)).toBeLessThan(-3);
    expect(Math.max(...xs)).toBeGreaterThan(11);
  });

  it('is left out where the model says the thing casts none', () => {
    expect(drawn(house({ shadow: null })).marks('shadow')).toHaveLength(0);
  });

  it('but a raised bed keeps its own side, which is not the sun\'s doing', () => {
    const bed = shape('bed', 'planting', box(0, 0, 3, 1.5), { raised: 0.5, shadow: null });
    expect(drawn(bed).under.querySelectorAll('[data-mark="shadow"]')).toHaveLength(1);
  });
});

describe('the corner a road turns (doc 98)', () => {
  const bent = (extra = {}) => shape('street', 'paving', box(0, 4, 12, 20),
    { line: [{ x: -6, y: 0 }, { x: 0, y: 0 }, { x: 0, y: 12 }], ...extra });

  it('is a disc of the band\'s own width, not of the outline\'s reach', () => {
    // A way that bends: its outline is twelve metres across because of the
    // bend, and the road is six wide. A disc from the outline would be twice
    // the road.
    const marks = drawn(bent({ bandWidth: 6 })).under.querySelectorAll('[data-mark="joins"]');
    expect(marks).toHaveLength(1);
    const radii = [...(marks[0]!.getAttribute('d') ?? '').matchAll(/a([\d.]+),/g)]
      .map((m) => Number(m[1]));
    expect(radii.every((r) => Math.abs(r - 3) < 0.01)).toBe(true);
  });

  it('sits at each end of the centreline, where the next way starts', () => {
    const d = drawn(bent({ bandWidth: 6 })).under
      .querySelector('[data-mark="joins"]')!.getAttribute('d') ?? '';
    // Two discs: one at (-6, 0), one at (0, 12) — in SVG, y the other way up.
    expect(d).toContain('M-9,0');
    expect(d).toContain('M-3,-12');
  });

  it('and a way with no line of its own draws none', () => {
    expect(drawn(shape('street', 'paving', box(0, 0, 10, 6))).marks('joins')).toHaveLength(0);
  });
});
