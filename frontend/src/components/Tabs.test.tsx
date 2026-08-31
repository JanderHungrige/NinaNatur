import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Tabs } from './Tabs';

describe('Tabs', () => {
  it('shows which one is open', () => {
    render(<Tabs active="draw" onPick={vi.fn()} />);
    expect(screen.getByRole('tab', { name: 'Zeichnen' }).getAttribute('aria-selected')).toBe('true');
    expect(screen.getByRole('tab', { name: 'Säen' }).getAttribute('aria-selected')).toBe('false');
  });

  it('switches on a click', () => {
    const onPick = vi.fn();
    render(<Tabs active="draw" onPick={onPick} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Säen' }));
    expect(onPick).toHaveBeenCalledWith('sow');
  });

  it('moves with the arrow keys, as a tablist should', () => {
    // A keyboard reaches a tablist with one Tab press and then the arrows.
    const onPick = vi.fn();
    render(<Tabs active="draw" onPick={onPick} />);
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Zeichnen' }), { key: 'ArrowRight' });
    expect(onPick).toHaveBeenCalledWith('sow');
  });

  it('wraps around at the end', () => {
    const onPick = vi.fn();
    render(<Tabs active="sow" onPick={onPick} />);
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Säen' }), { key: 'ArrowRight' });
    expect(onPick).toHaveBeenCalledWith('draw');
  });

  it('keeps only the open tab in the tab order', () => {
    render(<Tabs active="draw" onPick={vi.fn()} />);
    expect(screen.getByRole('tab', { name: 'Zeichnen' }).getAttribute('tabindex')).toBe('0');
    expect(screen.getByRole('tab', { name: 'Säen' }).getAttribute('tabindex')).toBe('-1');
  });

  it('says what each side is for', () => {
    render(<Tabs active="sow" onPick={vi.fn()} />);
    expect(screen.getByText(/Blühjahr/)).toBeDefined();
  });
});
