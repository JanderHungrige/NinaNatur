import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { fakeClient, openWorkspace, resetApp, start, stubMatchMedia } from './testing/appFixtures';
import { lightMap } from './testing/gardens';

const bedButton = (): HTMLElement => {
  const found = document.querySelector('.bed-list button');
  if (!(found instanceof HTMLElement)) throw new Error('no bed in the bed list');
  return found;
};

beforeEach(stubMatchMedia);
afterEach(resetApp);

describe('App — the front door', () => {
  it('asks the client it was given, and opens no workspace', async () => {
    const client = fakeClient();
    start(client);
    await waitFor(() => expect(client.stats).toHaveBeenCalled());
    expect(screen.queryByRole('toolbar')).toBeNull();
    expect(screen.queryByRole('complementary')).toBeNull();
  });
});

describe('App — a garden is a workspace', () => {
  it('opens the garden in the address as one banner, main, details and dock', async () => {
    await openWorkspace(fakeClient());
    for (const role of ['banner', 'main', 'contentinfo'] as const) {
      expect(screen.getAllByRole(role)).toHaveLength(1);
    }
    expect(screen.getAllByRole('complementary', { name: 'Details' })).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 1, name: 'Testgarten' })).toBeDefined();
    expect(screen.getByRole('toolbar', { name: 'Werkzeuge' })).toBeDefined();
  });

  it('asks for a bed’s suggestions when the bed is chosen, and lists them', async () => {
    const client = fakeClient();
    await openWorkspace(client);
    fireEvent.click(bedButton());
    await screen.findByText('Sambucus nigra');
    expect(client.bedSuggestions).toHaveBeenCalledWith('tok', 1, {});
  });

  it('puts an armed tool down on Escape, and the rail shows it', async () => {
    await openWorkspace(fakeClient());
    const rect = screen.getByRole('button', { name: 'Rechteck' });
    fireEvent.click(rect);
    expect(rect.getAttribute('aria-pressed')).toBe('true');
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(rect.getAttribute('aria-pressed')).toBe('false');
  });

  it('has nothing to undo when a garden has just opened', async () => {
    await openWorkspace(fakeClient());
    const undo = screen.getByRole('button', { name: 'Letzte Änderung rückgängig' });
    expect((undo as HTMLButtonElement).disabled).toBe(true);
  });

  it('computes the shade from the header when there is no map yet, then shows it', async () => {
    // It was disabled until somebody found the rebuild in the panel, and a
    // disabled button wore the busy cursor: a new garden's shade looked as if
    // it were loading for ever (the owner, 2026-09-21).
    const client = fakeClient({ rebuildLightMap: vi.fn(async () => lightMap()) });
    await openWorkspace(client);
    const shade = screen.getByRole('button', { name: 'Sonne & Schatten' }) as HTMLButtonElement;
    expect(shade.disabled).toBe(false);
    fireEvent.click(shade);
    expect(client.rebuildLightMap).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(shade.getAttribute('aria-pressed')).toBe('true'));
  });

  it('puts the map over the plan from the header once there is one', async () => {
    await openWorkspace(fakeClient({ lightMap: vi.fn(async () => lightMap()) }));
    const shade = screen.getByRole('button', { name: 'Sonne & Schatten' });
    await waitFor(() => expect((shade as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(shade);
    expect(shade.getAttribute('aria-pressed')).toBe('true');
  });
});

describe('App — one garden does not leak into the next', () => {
  it('starts a garden opened after another with nothing selected', async () => {
    // A bed chosen in one garden stayed chosen in the next: going home reset
    // eight of thirty-six pieces of state, and opening a garden reset none.
    const client = fakeClient();
    await openWorkspace(client);
    fireEvent.click(bedButton());
    await screen.findByText('Sambucus nigra');

    fireEvent.click(screen.getByRole('button', { name: 'Zur Startseite' }));
    fireEvent.change(await screen.findByLabelText('Garten-ID'), { target: { value: 'tok2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Garten öffnen' }));
    await screen.findByText('Zweitgarten geladen.');

    expect(bedButton().getAttribute('aria-pressed')).toBe('false');
    expect(screen.queryByText('Sambucus nigra')).toBeNull();
  });
});

describe('App — failures are said', () => {
  it('reports a failed planting and keeps it until it is closed', async () => {
    const client = fakeClient({
      plant: vi.fn(async () => {
        throw new Error('Netzwerkfehler');
      }),
    });
    await openWorkspace(client);
    fireEvent.click(bedButton());
    fireEvent.click(await screen.findByRole('button', { name: 'Sambucus nigra pflanzen' }));
    await screen.findByText('Pflanzen fehlgeschlagen: Netzwerkfehler');
    expect(screen.getByRole('button', { name: 'Schließen' })).toBeDefined();
  });
});
