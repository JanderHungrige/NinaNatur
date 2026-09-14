import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ShortcutHelp } from './ShortcutHelp';

/* Doc 92: the keyboard's shortcuts, as a modal dialog. */

describe('ShortcutHelp', () => {
  it('is a dialog named Tastenkürzel, there only while it is open', () => {
    const { rerender } = render(<ShortcutHelp open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole('dialog')).toBeNull();
    rerender(<ShortcutHelp open onClose={vi.fn()} />);
    expect(screen.getByRole('dialog', { name: 'Tastenkürzel' })).toBeDefined();
  });

  it('lists the shortcuts under where they apply, every key as a key', () => {
    render(<ShortcutHelp open onClose={vi.fn()} />);
    const help = screen.getByRole('dialog', { name: 'Tastenkürzel' });
    expect(within(help).getByRole('heading', { name: 'Überall' })).toBeDefined();
    expect(within(help).getByRole('heading', { name: 'In den Vorschlägen' })).toBeDefined();
    expect([...help.querySelectorAll('kbd')].map((key) => key.textContent)).toContain('Strg');
    // One sentence for the Mac, rather than every chord twice.
    expect(help.textContent).toMatch(/⌘/);
  });

  it('takes the focus when it opens', () => {
    render(<ShortcutHelp open onClose={vi.fn()} />);
    expect(screen.getByRole('dialog').contains(document.activeElement)).toBe(true);
  });

  it('closes with Schließen', () => {
    const onClose = vi.fn();
    render(<ShortcutHelp open onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: 'Schließen' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('closes on Escape, and no key pressed in it reaches the page', () => {
    // The page's Escape clears the selection (doc 88), and its Ctrl+Z would
    // take back a change nobody can see behind the help.
    const heard = vi.fn();
    window.addEventListener('keydown', heard);
    const onClose = vi.fn();
    render(<ShortcutHelp open onClose={onClose} />);
    const close = screen.getByRole('button', { name: 'Schließen' });
    fireEvent.keyDown(close, { key: 'z', ctrlKey: true });
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.keyDown(close, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
    expect(heard).not.toHaveBeenCalled();
    window.removeEventListener('keydown', heard);
  });

  it('keeps the page from hearing a key while it is open, even with the focus outside it', () => {
    // A click on the help's words leaves the focus on the page's body, and the
    // Escape that closes the help from there would clear the selection too.
    const heard = vi.fn();
    window.addEventListener('keydown', heard);
    const { rerender } = render(<ShortcutHelp open onClose={vi.fn()} />);
    fireEvent.keyDown(document.body, { key: 'Escape' });
    fireEvent.keyDown(document.body, { key: 'z', ctrlKey: true });
    expect(heard).not.toHaveBeenCalled();
    rerender(<ShortcutHelp open={false} onClose={vi.fn()} />);
    fireEvent.keyDown(document.body, { key: 'Escape' });
    expect(heard).toHaveBeenCalledTimes(1);
    window.removeEventListener('keydown', heard);
  });
});
