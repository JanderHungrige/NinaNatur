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

  it('keeps the arrow when the upper edge is two walls, and draws it from the longer', () => {
    // A notch in the upper wall: the server sends both pieces (review, 2026-09-21).
    const pent = shape('house', 'building', box(0, 0, 8, 4), {
      roof: 'pent',
      roofLines: [[{ x: -4, y: 2 }, { x: 2, y: 2 }], [{ x: 3, y: 2 }, { x: 4, y: 2 }]],
    });
    const d = drawn(pent).marks('roof')[0]!.getAttribute('d')!;
    // Two edges, then the shaft and its barbs.
    expect(d.match(/M/g)).toHaveLength(5);
    // The shaft starts a quarter of the way from the longer edge's middle (-1, 2)
    // to the house's centre (0, 0): at (-0.75, 1.5), y flipped in the drawing.
    expect(d).toContain('M-0.75,-1.5L');
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
    const ink = container.querySelector('[data-mark="roads"] > path')!;
    const mask = container.querySelector('mask')!;
    // The mask is the bands and the corners they turn, in two paths: in one, a
    // disc winding the other way cancels against its band and opens a hole.
    const cut = [...mask.querySelectorAll('path')].map((p) => p.getAttribute('d')).join('');
    // One line for both bands, and the mask's cut-out is that same line: what
    // lies on a road is hidden, so nothing crosses the junction.
    expect(ink.getAttribute('d')).toBe(cut);
    expect(ink.getAttribute('mask')).toBe(`url(#${mask.getAttribute('id')})`);
    expect(mask.querySelector('rect')!.getAttribute('fill')).toBe('#ffffff');
    expect(mask.querySelector('path')!.getAttribute('fill')).toBe('#000000');
    // Grown by most of a pixel, so a way ending on another way's edge cannot
    // leave a hairline of ink lying across the road.
    for (const path of mask.querySelectorAll('path')) {
      expect(Number(path.getAttribute('stroke-width'))).toBeGreaterThan(0);
    }
    // A road that turns is rounded, in the wash and in the line alike.
    expect(cut).toContain('a');
  });

  /* The owner, 2026-09-21: a house standing over a street was drawn over the
     road's grey, and the road's line still ran straight through it. */
  const houseOnRoad = shape('house', 'building', box(0, 1, 8, 6));
  const built = (shapes: DecoratedShape[]) => render(
    <svg><Plan shapes={shapes} metresPerPixel={0.05} /></svg>,
  ).container.querySelector('mask [data-mark="built"]');

  it('keeps its line out of a house that stands on the road', () => {
    const cut = built([across, houseOnRoad])!;
    expect(cut.getAttribute('fill')).toBe('#000000');
    // The house's outline, as it is drawn: from -4..4 across, -2..4 up.
    expect(cut.getAttribute('d')).toContain('-4,2');
    expect(cut.getAttribute('d')).toContain('4,-4');
  });

  it('follows a house while it is dragged, not where it stood', () => {
    // Dragged 20 m east, off the road: the cut goes with it (review, 2026-09-21).
    const { container } = render(<svg><Plan shapes={[across, houseOnRoad]} metresPerPixel={0.05}
      moving={{ key: houseOnRoad.key, dx: 20, dy: 0 }} /></svg>);
    const d = container.querySelector('mask [data-mark="built"]')!.getAttribute('d') ?? '';
    expect(d).toContain('16,2');
    expect(d).not.toContain('-4,2');
  });

  it('but not out of what grows or lies there', () => {
    expect(built([across, shape('tree', 'crown', box(0, 0, 6, 6))])).toBeNull();
    expect(built([across, shape('lawn', 'grass', box(0, 0, 6, 6))])).toBeNull();
  });

  it('turns every built outline the same way, so two that overlap do not cancel', () => {
    const turned = shape('shed', 'building', [...box(2, 1, 4, 4)].reverse());
    const d = built([across, houseOnRoad, turned])!.getAttribute('d') ?? '';
    const areas = d.split('Z').filter(Boolean).map((ring) => {
      const pts = [...ring.matchAll(/(-?[\d.]+),(-?[\d.]+)/g)].map((m) => [Number(m[1]), Number(m[2])]);
      return pts.reduce((sum, p, i) => {
        const q = pts[(i + 1) % pts.length]!;
        return sum + p[0]! * q[1]! - q[0]! * p[1]!;
      }, 0);
    });
    expect(areas).toHaveLength(2);
    expect(Math.sign(areas[0]!)).toBe(Math.sign(areas[1]!));
  });

  it('holds the rounded ends in its mask, so they keep their line', () => {
    // The band ends at ±18 m and its disc, 3 m round, reaches 21 m.
    const { container } = render(<svg><Plan shapes={[across]} metresPerPixel={0.05} /></svg>);
    const mask = container.querySelector('mask')!;
    expect(Number(mask.getAttribute('x'))).toBeLessThan(-21);
    expect(Number(mask.getAttribute('x')) + Number(mask.getAttribute('width'))).toBeGreaterThan(21);
  });

  it('and draws nothing at all where a garden has no street', () => {
    const { container } = render(<svg><Plan shapes={[]} metresPerPixel={0.05} /></svg>);
    expect(container.querySelector('[data-mark="roads"]')).toBeNull();
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
