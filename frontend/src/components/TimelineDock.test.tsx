import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { TimelineDock } from './TimelineDock';

function dock(open: boolean) {
  const onToggle = vi.fn();
  render(
    <TimelineDock
      open={open}
      onToggle={onToggle}
      player={<button type="button">Nächster Monat</button>}
    >
      <p>Die Monatstabelle</p>
    </TimelineDock>,
  );
  return onToggle;
}

function bodyOf(toggle: HTMLElement): HTMLElement | null {
  return document.getElementById(toggle.getAttribute('aria-controls') ?? '');
}

describe('TimelineDock', () => {
  it('is the page’s contentinfo, and holds the bloom year', () => {
    dock(true);
    expect(screen.getByRole('contentinfo').textContent).toContain('Die Monatstabelle');
  });

  it('is a heading whose button says whether the year is shown, and what it controls', () => {
    // Jahreslauf, not Blühjahr: the table inside already has that heading, and
    // two headings of one name are read out twice.
    dock(true);
    const toggle = screen.getByRole('button', { name: 'Jahreslauf' });
    expect(toggle.closest('h2')).not.toBeNull();
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(bodyOf(toggle)?.textContent).toContain('Die Monatstabelle');
  });

  it('folds the timeline away and keeps the player', () => {
    // Stepping through the months still moves the plan; only the table goes.
    dock(false);
    const toggle = screen.getByRole('button', { name: 'Jahreslauf' });
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect(bodyOf(toggle)?.hidden).toBe(true);
    expect(screen.getByRole('button', { name: 'Nächster Monat' })).toBeDefined();
  });

  it('asks to change rather than changing by itself', () => {
    const onToggle = dock(true);
    fireEvent.click(screen.getByRole('button', { name: 'Jahreslauf' }));
    expect(onToggle).toHaveBeenCalledWith(false);
  });
});
