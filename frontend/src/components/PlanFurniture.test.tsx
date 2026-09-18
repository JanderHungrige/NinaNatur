import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { scaleBar } from '../canvas/scaleBar';
import { PlanThemeProvider } from '../themes/context';
import { draftSketch } from '../themes/draft-sketch';
import { technisch } from '../themes/technisch';
import type { PlanTheme } from '../themes/types';
import { PlanCredit } from './PlanCredit';
import { PlanFurniture } from './PlanFurniture';

/* The plan's north, scale and title, and whose style it is (doc 98). */

function corner(theme: PlanTheme, metresPerPixel = 0.1) {
  return render(
    <PlanThemeProvider theme={theme}>
      <PlanFurniture metresPerPixel={metresPerPixel} title="Musterblatt"
                     updatedAt="2026-09-18T10:00:00+00:00" />
      <PlanCredit />
    </PlanThemeProvider>,
  );
}

describe('the plan\'s furniture', () => {
  it('says north, a true scale and the garden\'s name and date in Draft Sketch', () => {
    const { container, getByRole } = corner(draftSketch, 0.1);
    expect(container.querySelector('.plan-furniture__north')).not.toBeNull();
    const bar = scaleBar(0.1, 56);
    expect(getByRole('img').getAttribute('aria-label')).toBe(`Maßstabsleiste: ${bar.metres} m`);
    expect(container.textContent).toContain('Musterblatt');
    expect(container.textContent).toContain('Stand 18.9.2026');
  });

  it('draws the bar exactly as long as the length it names', () => {
    const { container } = corner(draftSketch, 0.25);
    const svg = container.querySelector('.plan-furniture__scale svg')!;
    const bar = scaleBar(0.25, 56);
    expect(Number(svg.getAttribute('width')) - 8).toBeCloseTo(bar.pixels, 0);
  });

  it('gives his credit beneath the plan, word for word, and nothing for Technisch', () => {
    expect(corner(draftSketch).container.querySelector('.plan-credit')?.textContent).toBe(
      'Zeichenstil nach Draft Sketch von Warren Davison, verwendet und angepasst mit seiner '
      + 'Erlaubnis · with assistance from Louis Hill (@NKYmapLAB)');
    const plain = corner(technisch).container;
    expect(plain.querySelector('.plan-furniture')).toBeNull();
    expect(plain.textContent).toBe('');
  });
});
