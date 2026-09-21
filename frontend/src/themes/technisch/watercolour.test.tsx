import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { TechnischSymbols } from './symbols';

/** The owner's check, #1 and #2: in metres alone the wobble moved a zoomed-in
 *  bed sixty pixels off the corners it was drawn through. */
describe('Technisch — the hand-drawn edge', () => {
  const scale = (metresPerPixel: number) => {
    const { container } = render(<svg><defs><TechnischSymbols metresPerPixel={metresPerPixel} /></defs></svg>);
    return Number(container.querySelector('#watercolour feDisplacementMap')?.getAttribute('scale'));
  };

  it('wanders as far as it always did at an ordinary zoom', () => {
    expect(scale(0.0625)).toBeCloseTo(0.3, 9);
  });

  it('never wanders more than seven pixels when zoomed right in', () => {
    const metresPerPixel = 0.002;
    expect(scale(metresPerPixel) / metresPerPixel).toBeCloseTo(7, 6);
  });
});
