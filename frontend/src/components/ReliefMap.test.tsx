import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { Terrain } from '../api/client';
import { ReliefMap } from './ReliefMap';

function terrain(relief: number[], cols = 2, rows = 2): Terrain {
  return {
    cell_m: 1, min_x: 0, min_y: 0, cols, rows, relief,
    lowest: 100, highest: 102, source: 'Nordrhein-Westfalen',
    licence: 'dl-de/zero-2-0', attribution: '© Geobasis NRW', vertical_step_m: 0.01,
  };
}

function svg(node: React.ReactElement): SVGSVGElement {
  const { container } = render(<svg>{node}</svg>);
  return container.querySelector('svg') as SVGSVGElement;
}

describe('ReliefMap', () => {
  it('draws nothing at all for level ground', () => {
    // Not a grid of invisible rectangles: 40,000 of those is a real cost in a
    // canvas that is redrawn on every pan.
    const flat = svg(<ReliefMap terrain={terrain([0.5, 0.5, 0.5, 0.5])} />);
    expect(flat.querySelectorAll('rect')).toHaveLength(0);
  });

  it('draws the lit and the shadowed side in different inks', () => {
    const slope = svg(<ReliefMap terrain={terrain([0.1, 0.9, 0.5, 0.5])} />);
    const rects = [...slope.querySelectorAll('rect')];

    expect(rects).toHaveLength(2);
    expect(new Set(rects.map((r) => r.getAttribute('fill')))).toHaveProperty('size', 2);
  });

  it('puts a row where the garden puts it, not where the SVG counts', () => {
    // The canvas draws y downwards while the grid counts rows northwards.
    // Getting this wrong mirrors the relief and puts every hillside on the
    // wrong side of the plan — and it would look entirely plausible.
    const two = svg(<ReliefMap terrain={terrain([0.1, 0.1, 0.9, 0.9])} />);
    const rects = [...two.querySelectorAll('rect')];
    const southern = rects.filter((r) => r.getAttribute('fill')?.includes('dark'));
    const northern = rects.filter((r) => !r.getAttribute('fill')?.includes('dark'));

    expect(Number(southern[0]?.getAttribute('y'))).toBeGreaterThan(
      Number(northern[0]?.getAttribute('y')),
    );
  });

  it('is faint enough to place a bed over', () => {
    const steep = svg(<ReliefMap terrain={terrain([0.0, 1.0, 0.5, 0.5])} />);
    for (const rect of steep.querySelectorAll('rect')) {
      expect(Number(rect.getAttribute('opacity'))).toBeLessThanOrEqual(0.25);
    }
  });

  it('is hidden from screen readers, having nothing to say to them', () => {
    const any = svg(<ReliefMap terrain={terrain([0.1, 0.9, 0.5, 0.5])} />);
    expect(any.querySelector('.relief-map')?.getAttribute('aria-hidden')).toBe('true');
  });
});
