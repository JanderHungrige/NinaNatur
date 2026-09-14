import { fireEvent, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
  details,
  fakeClient,
  onPlan,
  openWorkspace,
  resetApp,
  stubMatchMedia,
  stubWideLayout,
  viewHeading,
} from './testing/appFixtures';

/*
 * Doc 91: below 66rem the workspace is the window — the plan, a bar of tools at
 * its foot, and the details as a sheet from below. jsdom lays nothing out, so
 * these flows pin structure, state and keys; the layout is measured on the
 * preview.
 */

const splitter = () => screen.getByRole('separator', { name: 'Höhe der Details' });
const workspace = () => screen.getByRole('main');
const yearToggle = () => within(screen.getByRole('contentinfo')).getByRole('button', { name: 'Jahreslauf' });
const inert = (selector: string) => document.querySelector(selector)?.hasAttribute('inert');

afterEach(resetApp);

describe('App — a narrow window: the details as a sheet from below', () => {
  beforeEach(stubMatchMedia);

  it('opens with the sheet resting at a quarter and the year folded', async () => {
    await openWorkspace(fakeClient());
    expect(workspace().getAttribute('data-sheet')).toBe('peek');
    expect(splitter().getAttribute('aria-valuenow')).toBe('25');
    expect(yearToggle().getAttribute('aria-expanded')).toBe('false');
  });

  it('keeps the page’s landmarks where doc 87 put them', async () => {
    await openWorkspace(fakeClient());
    expect(screen.getByRole('contentinfo').closest('main')).toBeNull();
    expect(details().closest('main')).toBe(workspace());
    expect(details().contains(splitter())).toBe(true);
  });

  it('says a bed tapped on the plan in the resting sheet, without raising it', async () => {
    await openWorkspace(fakeClient());
    fireEvent.click(onPlan('polygon[data-element-id="1"]'));
    expect(viewHeading()?.textContent).toBe('Südbeet');
    expect(workspace().getAttribute('data-sheet')).toBe('peek');
  });

  it('rises with the keyboard, holds everything else inert at 90 %, and comes down on Escape keeping the bed', async () => {
    await openWorkspace(fakeClient());
    fireEvent.click(onPlan('polygon[data-element-id="1"]'));
    splitter().focus();
    fireEvent.keyDown(splitter(), { key: 'ArrowUp' });
    expect(workspace().getAttribute('data-sheet')).toBe('half');
    expect(inert('.site-header')).toBe(false);
    fireEvent.keyDown(splitter(), { key: 'End' });
    expect(workspace().getAttribute('data-sheet')).toBe('full');
    for (const selector of ['.site-header', '.workspace__plan', '.tool-rail', '.timeline-dock']) {
      expect(inert(selector), selector).toBe(true);
    }
    expect(inert('aside.inspector')).toBe(false);
    // The toast is a live region: it has to stay perceivable.
    expect(inert('.status-toast')).toBe(false);
    fireEvent.keyDown(splitter(), { key: 'Escape' });
    expect(workspace().getAttribute('data-sheet')).toBe('half');
    expect(inert('.site-header')).toBe(false);
    expect(viewHeading()?.textContent).toBe('Südbeet');
  });

  it('keeps the year’s fold for a narrow window apart from the wide one', async () => {
    await openWorkspace(fakeClient());
    fireEvent.click(yearToggle());
    expect(yearToggle().getAttribute('aria-expanded')).toBe('true');
    expect(window.localStorage.getItem('ninanatur.dock.open.narrow')).toBe('true');
    expect(window.localStorage.getItem('ninanatur.dock.open')).toBeNull();
    window.localStorage.clear();
  });

  it('keeps the shade switch behind Menü in the header', async () => {
    await openWorkspace(fakeClient());
    const banner = screen.getByRole('banner');
    const menu = within(banner).getByRole('button', { name: 'Menü' });
    const more = document.getElementById(menu.getAttribute('aria-controls') ?? '');
    expect(more?.contains(within(banner).getByRole('button', { name: 'Sonne & Schatten' }))).toBe(true);
  });
});

describe('App — a wide window keeps the workspace doc 87 built', () => {
  beforeEach(stubWideLayout);

  it('has no sheet and no handle, and the year stands open', async () => {
    await openWorkspace(fakeClient());
    expect(workspace().hasAttribute('data-sheet')).toBe(false);
    expect(screen.queryByRole('separator')).toBeNull();
    expect(yearToggle().getAttribute('aria-expanded')).toBe('true');
  });
});
