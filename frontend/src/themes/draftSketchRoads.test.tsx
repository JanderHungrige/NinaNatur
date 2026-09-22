import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { Point } from '../canvas/viewport';
import { draftSketch } from './draft-sketch';
import type { DecoratedShape } from './types';

/* The street network's line in his hand (doc 98): once round the network, and
   never through a junction or a house. Split from draftSketchVocabulary.test
   when the owner's check of 2026-09-21 added the houses. */

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
  };
}

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
