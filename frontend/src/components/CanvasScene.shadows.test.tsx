import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { GardenCanvas } from './GardenCanvas';

/*
 * One moment of the day's shadows (doc 116): every shadow as rings, outlines
 * anticlockwise and holes clockwise, drawn as one path under the non-zero rule.
 * One element per ring, as it used to be, fills a courtyard's hole with its own
 * outline and darkens where two shadows overlap.
 */

function frame(shadows: number[][][]) {
  const { container } = render(
    <GardenCanvas
      garden={{
        unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {},
        share_token: 'tok', name: 'G', latitude: 52.5, longitude: 13.4,
        created_at: '', updated_at: '', beds: [], obstacles: [],
      }}
      selectedBedId={null} onSelectBed={vi.fn()} size={{ widthPx: 800, heightPx: 600 }}
      shadows={shadows}
    />,
  );
  return container.querySelector('g.day-shadows')!;
}

/** A house round a courtyard whose shadow keeps a lit hole, as the server sends it. */
const OUTLINE = [[0, 0], [10, 0], [10, 10], [0, 10]];
const HOLE = [[3, 3], [3, 6], [6, 6], [6, 3]];

describe('the day\'s shadows at one moment', () => {
  it('are one path under the non-zero rule, holes and all', () => {
    const drawn = frame([OUTLINE, HOLE, [[20, 0], [24, 0], [24, 4], [20, 4]]]);
    expect(drawn.querySelectorAll('polygon')).toHaveLength(0);
    const [path, ...more] = [...drawn.children];
    expect(more).toHaveLength(0);
    expect(path!.tagName).toBe('path');
    expect(path!.getAttribute('fill-rule')).toBe('nonzero');
    expect((path!.getAttribute('d') ?? '').match(/M/g)).toHaveLength(3);
  });

  it('keep a hole wound against its outline, so the fill leaves it open', () => {
    const d = frame([OUTLINE, HOLE]).querySelector('path')!.getAttribute('d') ?? '';
    const rings = d.split('M').filter(Boolean).map((ring) =>
      ring.replace('Z', '').split('L').map((p) => p.split(',').map(Number)));
    const turned = (ring: number[][]) => ring.reduce((sum, a, i) => {
      const b = ring[(i + 1) % ring.length]!;
      return sum + a[0]! * b[1]! - b[0]! * a[1]!;
    }, 0);
    // Drawn with y flipped, both turn the other way — and still against each other.
    expect(Math.sign(turned(rings[0]!))).toBe(-Math.sign(turned(rings[1]!)));
  });
});
