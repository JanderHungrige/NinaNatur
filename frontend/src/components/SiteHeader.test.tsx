import { fireEvent, render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { SiteHeader } from './SiteHeader';

/* Doc 91: on a narrow window the header is one row, and the rest is behind Menü. */

function header(more?: ReactNode) {
  const props = {
    version: 'V0.20.test',
    onHome: vi.fn(),
    onFeedback: vi.fn(),
    accountBar: { username: null, onSignIn: vi.fn(), onSignUp: vi.fn(), onSignOut: vi.fn(), inviting: false },
    busy: false,
  };
  render(
    <SiteHeader {...props} more={more}>
      <button type="button">Letzte Änderung rückgängig</button>
    </SiteHeader>,
  );
  return props;
}

const menu = () => screen.getByRole('button', { name: 'Menü' });
const region = () => document.getElementById(menu().getAttribute('aria-controls') ?? '');

describe('SiteHeader', () => {
  it('keeps the garden’s own controls in the row, out of the menu', () => {
    header(<button type="button">Sonne &amp; Schatten</button>);
    expect(region()?.contains(screen.getByRole('button', { name: 'Letzte Änderung rückgängig' }))).toBe(false);
  });

  it('puts the version, what it is given as more, feedback and the account behind Menü', () => {
    header(<button type="button">Sonne &amp; Schatten</button>);
    const more = region();
    for (const name of ['Sonne & Schatten', 'Rückmeldung', 'Anmelden', 'Konto anlegen']) {
      expect(more?.contains(screen.getByRole('button', { name }))).toBe(true);
    }
    expect(more?.textContent).toMatch(/V0\.20\.test/);
  });

  it('opens and closes the menu, and says whether it is open', () => {
    header();
    expect(menu().getAttribute('aria-expanded')).toBe('false');
    expect(region()?.getAttribute('data-open')).toBe('false');
    fireEvent.click(menu());
    expect(menu().getAttribute('aria-expanded')).toBe('true');
    expect(region()?.getAttribute('data-open')).toBe('true');
    fireEvent.click(menu());
    expect(menu().getAttribute('aria-expanded')).toBe('false');
  });

  it('closes on Escape, gives the focus back to Menü, and the page’s Escape never hears it', () => {
    const heard = vi.fn();
    window.addEventListener('keydown', heard);
    header();
    fireEvent.click(menu());
    const feedback = screen.getByRole('button', { name: 'Rückmeldung' });
    feedback.focus();
    fireEvent.keyDown(feedback, { key: 'Escape' });
    expect(menu().getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(menu());
    expect(heard).not.toHaveBeenCalled();
    window.removeEventListener('keydown', heard);
  });

  it('lets Escape through while the menu is closed', () => {
    const heard = vi.fn();
    window.addEventListener('keydown', heard);
    header();
    fireEvent.keyDown(menu(), { key: 'Escape' });
    expect(heard).toHaveBeenCalledTimes(1);
    window.removeEventListener('keydown', heard);
  });

  it('closes once something in it is pressed, after doing it', () => {
    const props = header();
    fireEvent.click(menu());
    fireEvent.click(screen.getByRole('button', { name: 'Rückmeldung' }));
    expect(props.onFeedback).toHaveBeenCalled();
    expect(menu().getAttribute('aria-expanded')).toBe('false');
  });

  it('closes when a pointer goes down outside it, and not inside', () => {
    header();
    fireEvent.click(menu());
    fireEvent.pointerDown(region()!);
    expect(menu().getAttribute('aria-expanded')).toBe('true');
    fireEvent.pointerDown(document.body);
    expect(menu().getAttribute('aria-expanded')).toBe('false');
  });
});
