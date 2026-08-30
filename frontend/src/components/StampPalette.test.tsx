import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { StampPalette } from './StampPalette';

function show(selected: string | null = null) {
  const onPick = vi.fn();
  render(<StampPalette selected={selected} onPick={onPick} busy={false} />);
  return onPick;
}

describe('StampPalette', () => {
  it('offers what a garden is made of, in German', () => {
    show();
    for (const label of ['Wohnhaus', 'Rasen', 'Pflaster', 'Kies', 'Teich', 'Eiche']) {
      expect(screen.getByRole('button', { name: new RegExp(label) })).toBeDefined();
    }
  });

  it('picks an element', () => {
    const onPick = show();
    fireEvent.click(screen.getByRole('button', { name: /Wohnhaus/ }));
    expect(onPick).toHaveBeenCalledWith('house');
  });

  it('shows which one is armed', () => {
    show('house');
    expect(
      screen.getByRole('button', { name: /Wohnhaus/ }).getAttribute('aria-pressed'),
    ).toBe('true');
  });

  it('picking the armed element disarms it', () => {
    // The same click that says "a house" is the one reached for to stop.
    const onPick = show('house');
    fireEvent.click(screen.getByRole('button', { name: /Wohnhaus/ }));
    expect(onPick).toHaveBeenCalledWith(null);
  });

  it('separates the name from the size for anything that reads it aloud', () => {
    // The two spans concatenate into "Wohnhaus10 × 8 m" without this.
    show();
    expect(screen.getByRole('button', { name: 'Wohnhaus, 10 × 8 m' })).toBeDefined();
  });

  it('says what each element brings with it', () => {
    // Choosing "Hecke" should answer a question, not ask one — the size is in
    // the label so nobody has to place one to find out.
    show();
    expect(screen.getByRole('button', { name: /Hecke.*6.*0,6/ })).toBeDefined();
  });

  it('groups surfaces apart from things that stand up', () => {
    show();
    expect(screen.getByRole('group', { name: /Bauten/ })).toBeDefined();
    expect(screen.getByRole('group', { name: /Flächen/ })).toBeDefined();
  });
});
