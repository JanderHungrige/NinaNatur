import { fireEvent, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { fakeClient, onPlan, openWorkspace, resetApp, stubMatchMedia, viewHeading } from './testing/appFixtures';

/* Doc 92: the keyboard's shortcuts, one key away. */

beforeEach(stubMatchMedia);
afterEach(resetApp);

describe('App — the keyboard’s shortcuts on ?', () => {
  it('opens the help on ?, and Escape closes it without dropping the chosen bed', async () => {
    await openWorkspace(fakeClient());
    fireEvent.click(onPlan('polygon[data-element-id="1"]'));
    expect(viewHeading()?.textContent).toBe('Südbeet');
    fireEvent.keyDown(window, { key: '?' });
    const help = screen.getByRole('dialog', { name: 'Tastenkürzel' });
    fireEvent.keyDown(within(help).getByRole('button', { name: 'Schließen' }), { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(viewHeading()?.textContent).toBe('Südbeet');
  });

  it('opens it from Tastenkürzel in the header, which names ?, and gives the focus back', async () => {
    await openWorkspace(fakeClient());
    const button = within(screen.getByRole('banner')).getByRole('button', { name: 'Tastenkürzel' });
    expect(button.getAttribute('aria-keyshortcuts')).toBe('?');
    expect(button.getAttribute('aria-haspopup')).toBe('dialog');
    button.focus();
    fireEvent.click(button);
    const help = screen.getByRole('dialog', { name: 'Tastenkürzel' });
    // Within the help: the toast has a Schließen of its own.
    fireEvent.click(within(help).getByRole('button', { name: 'Schließen' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(document.activeElement).toBe(button);
  });
});
