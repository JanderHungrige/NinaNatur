import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { CanopySuggestion } from '../api/client';
import { CanopyMarks } from './CanopyMarks';

const tree = (overrides: Partial<CanopySuggestion> = {}): CanopySuggestion =>
  ({ suggestion_id: 1, x: 12, y: -4, radius_m: 3.5, height_m: 14.2, ...overrides }) as CanopySuggestion;

function marks(trees: CanopySuggestion[]) {
  return render(
    <svg>
      <CanopyMarks trees={trees} />
    </svg>,
  ).container;
}

describe('CanopyMarks', () => {
  it('draws a dashed crown where each found tree stands', () => {
    // Doc 89: a tree the surface model found is a place on the plan, not only a
    // row of numbers in the details.
    const container = marks([tree(), tree({ suggestion_id: 2, x: -3, y: 8, radius_m: 2 })]);
    const crowns = container.querySelectorAll('circle.canopy-mark');
    expect(crowns).toHaveLength(2);
    // Garden metres, y flipped as everywhere on this plan.
    expect(crowns[0]?.getAttribute('cx')).toBe('12');
    expect(crowns[0]?.getAttribute('cy')).toBe('4');
    expect(crowns[0]?.getAttribute('r')).toBe('3.5');
  });

  it('is a mark, not an object: out of the accessibility tree and out of the pointer’s way', () => {
    // Doc 84: suggestions, never objects. A crown drawn over a bed must not take
    // the click meant for the bed.
    const group = marks([tree()]).querySelector('.canopy-marks');
    expect(group?.getAttribute('aria-hidden')).toBe('true');
    expect(group?.getAttribute('pointer-events')).toBe('none');
  });

  it('draws nothing when nothing was found', () => {
    expect(marks([]).querySelector('.canopy-marks')).toBeNull();
  });
});
