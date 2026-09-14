import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MonthStrip } from './MonthStrip';

const on = (container: HTMLElement) =>
  [...container.querySelectorAll('.month-strip__cell')].map((cell) =>
    cell.classList.contains('month-strip__cell--on'),
  );

describe('MonthStrip', () => {
  it('fills the flowering months among twelve', () => {
    const { container } = render(<MonthStrip start={6} end={7} />);
    const cells = on(container);
    expect(cells).toHaveLength(12);
    expect(cells.flatMap((lit, index) => (lit ? [index + 1] : []))).toEqual([6, 7]);
  });

  it('wraps across the new year', () => {
    const { container } = render(<MonthStrip start={11} end={2} />);
    expect(on(container).flatMap((lit, index) => (lit ? [index + 1] : []))).toEqual([1, 2, 11, 12]);
  });

  it('says the months in words rather than as a picture of cells', () => {
    // Doc 90: twelve coloured boxes mean nothing to a screen reader.
    render(<MonthStrip start={6} end={7} />);
    expect(screen.getByRole('img', { name: 'Blüte Juni bis Juli' })).toBeDefined();
  });

  it('says when nobody knows, instead of drawing an empty year', () => {
    // Doc 15: unknown stays unknown.
    render(<MonthStrip start={null} end={null} />);
    expect(screen.getByText('Blühzeit unbekannt')).toBeDefined();
    expect(screen.queryByRole('img')).toBeNull();
  });
});
