import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { viewBox } from '../canvas/viewport';
import { SHEET_GARDENS } from './gardens';
import { SheetCell, cellView } from './SheetCell';

/* One cell of the contact sheet: the app's own scene, and nothing drawn here (doc 95). */

const small = SHEET_GARDENS[0]!;

describe('SheetCell', () => {
  it('is the plan the app draws, in the paper the app draws it on', () => {
    const { container } = render(<SheetCell entry={small} spanM={40} sun={false} width={360} height={270} />);
    const svg = container.querySelector('svg.canvas');
    expect(svg).not.toBeNull();
    expect(svg?.getAttribute('viewBox')).toBe(viewBox(cellView(small, 40, 360, 270)));
  });

  it('draws every bed and every element of its garden', () => {
    const { container } = render(<SheetCell entry={small} spanM={40} sun={false} width={360} height={270} />);
    expect(container.querySelectorAll('polygon.bed')).toHaveLength(small.garden.beds.length);
    expect(container.querySelectorAll('polygon.obstacle')).toHaveLength(small.garden.obstacles.length);
  });

  it('shows what is in flower, as the app\'s own bloom dots', () => {
    const { container } = render(<SheetCell entry={small} spanM={12} sun={false} width={360} height={270} />);
    const coloured = [...container.querySelectorAll('circle.bloom-dot')]
      .filter((dot) => !(dot.getAttribute('fill') ?? '').includes('--ink-muted'));
    expect(coloured.length).toBeGreaterThan(0);
  });

  it('lays the sun map over the ground when asked', () => {
    const shaded = render(<SheetCell entry={small} spanM={40} sun width={360} height={270} />);
    expect(shaded.container.querySelector('.sun-map')).not.toBeNull();
    shaded.unmount();
    const plain = render(<SheetCell entry={small} spanM={40} sun={false} width={360} height={270} />);
    expect(plain.container.querySelector('.sun-map')).toBeNull();
  });
});
