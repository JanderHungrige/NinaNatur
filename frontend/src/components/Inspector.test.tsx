import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Inspector } from './Inspector';

describe('Inspector', () => {
  it('is the complementary region named Details, and holds what it is given', () => {
    render(
      <Inspector wide={false} onWide={vi.fn()}>
        <p>Beete</p>
      </Inspector>,
    );
    expect(screen.getByRole('complementary', { name: 'Details' }).textContent).toContain('Beete');
  });

  it('offers the wide view as a toggle that keeps its name and says its state', () => {
    // One name in both states: a label that flips *and* a pressed state tell a
    // screen reader the same thing twice, and one of them wrongly.
    const onWide = vi.fn();
    render(
      <Inspector wide={false} onWide={onWide}>
        <p />
      </Inspector>,
    );
    const toggle = screen.getByRole('button', { name: 'Breite Ansicht' });
    expect(toggle.getAttribute('aria-pressed')).toBe('false');
    fireEvent.click(toggle);
    expect(onWide).toHaveBeenCalledWith(true);
  });

  it('turns the wide view off again', () => {
    const onWide = vi.fn();
    render(
      <Inspector wide onWide={onWide}>
        <p />
      </Inspector>,
    );
    const toggle = screen.getByRole('button', { name: 'Breite Ansicht' });
    expect(toggle.getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(toggle);
    expect(onWide).toHaveBeenCalledWith(false);
  });
});
