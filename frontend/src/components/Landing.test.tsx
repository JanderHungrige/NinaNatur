import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { StatsOut } from '../api/client';
import { Landing } from './Landing';

const STATS: StatsOut = {
  species: 8939,
  species_with_full_site_profile: 4300,
  animal_partnerships: 303825,
  german_animals: 22169,
  german_names: 14602,
  sources: [
    { name: 'EIVE 1.0', licence: 'CC-BY-4.0', url: 'https://example.org/eive',
      contributes: 'Standortansprüche' },
    { name: 'GloBI', licence: 'CC0-1.0', url: 'https://example.org/globi',
      contributes: 'Beziehungen' },
  ],
};

function show(props: Partial<Parameters<typeof Landing>[0]> = {}) {
  const onCreate = vi.fn();
  const onOpen = vi.fn();
  render(
    <Landing
      createForm={
        <button type="button" onClick={onCreate}>
          Neuen Garten anlegen
        </button>
      }
      onOpen={onOpen}
      busy={false}
      loadStats={async () => STATS}
      {...props}
    />,
  );
  return { onCreate, onOpen };
}

describe('Landing', () => {
  it('says what the thing is', () => {
    show();
    expect(screen.getByRole('heading', { level: 1 })).toBeDefined();
  });

  it('states figures from the API, not from the markup', async () => {
    // Wave 1 typed "3.087" into its HTML and it was wrong the first time the
    // catalogue was rebuilt. A page that states a number is making a claim.
    show();
    await waitFor(() => expect(screen.getByText('8.939')).toBeDefined());
    expect(screen.getByText('303.825')).toBeDefined();
  });

  it('names its sources with their licences', async () => {
    show();
    await waitFor(() => expect(screen.getByText(/EIVE 1.0/)).toBeDefined());
    expect(screen.getByText(/CC0-1.0/)).toBeDefined();
  });

  it('still works when the figures cannot be loaded', async () => {
    // The front door must open even when the catalogue does not answer.
    show({ loadStats: async () => null });
    expect(screen.getByRole('heading', { level: 1 })).toBeDefined();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Garten öffnen' })).toBeDefined(),
    );
  });

  it('renders the create form it was given, rather than inventing a garden', () => {
    // A garden's latitude is not a detail: the solar model rests on it, and a
    // landing page that created gardens with a default would compute everyone's
    // light for Berlin.
    const { onCreate } = show();
    fireEvent.click(screen.getByRole('button', { name: /Neuen Garten anlegen/ }));
    expect(onCreate).toHaveBeenCalled();
  });

  it('opens a garden by its id', () => {
    const { onOpen } = show();
    fireEvent.change(screen.getByLabelText(/Garten-ID/), { target: { value: 'abc123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Garten öffnen' }));
    expect(onOpen).toHaveBeenCalledWith('abc123');
  });

  it('ignores stray whitespace around a pasted id', () => {
    const { onOpen } = show();
    fireEvent.change(screen.getByLabelText(/Garten-ID/), { target: { value: '  abc123 \n' } });
    fireEvent.click(screen.getByRole('button', { name: 'Garten öffnen' }));
    expect(onOpen).toHaveBeenCalledWith('abc123');
  });

  it('does not open nothing', () => {
    const { onOpen } = show();
    fireEvent.click(screen.getByRole('button', { name: 'Garten öffnen' }));
    expect(onOpen).not.toHaveBeenCalled();
  });

  it('shows a message when a garden could not be opened', () => {
    show({ problem: 'Dieser Link gehört zu keinem Garten (mehr).' });
    expect(screen.getByRole('alert')).toBeDefined();
  });
});

describe('Landing — opening a garden keeps it', () => {
  it('hands the id up so the caller can put it in the URL', () => {
    // Found by opening a garden by its id and reloading: the app returned to
    // the landing page, because nothing had written the fragment. The caller
    // owns the URL — and it must be the fragment, never a query parameter: the
    // token is a credential and a query string reaches the access log.
    const onOpen = vi.fn();
    render(
      <Landing
        createForm={null}
        onOpen={onOpen}
        busy={false}
        loadStats={async () => STATS}
      />,
    );
    fireEvent.change(screen.getByLabelText(/Garten-ID/), { target: { value: 'tok' } });
    fireEvent.click(screen.getByRole('button', { name: 'Garten öffnen' }));
    expect(onOpen).toHaveBeenCalledWith('tok');
  });
});

describe('Landing — one way in', () => {
  it('offers the map as the way to start', () => {
    render(
      <Landing
        createForm={<p>Formular</p>}
        mapPicker={<p>Karte</p>}
        onOpen={vi.fn()}
        busy={false}
        loadStats={async () => null}
      />,
    );
    expect(screen.getByRole('heading', { name: 'Auf der Karte anfangen' })).toBeDefined();
  });

  it('keeps the map-less way reachable, and quiet', () => {
    // Nominatim and Overpass are free services with no SLA. Without this,
    // a bad afternoon at either leaves nobody able to start at all.
    render(
      <Landing
        createForm={<p>Formular</p>}
        mapPicker={<p>Karte</p>}
        onOpen={vi.fn()}
        busy={false}
        loadStats={async () => null}
      />,
    );
    const aside = screen.getByText('Ohne Karte anfangen');
    expect(aside.tagName.toLowerCase()).toBe('summary');
    expect(screen.getByText('Formular')).toBeDefined();
  });

  it('no longer carries an account panel in the middle of the page', () => {
    // It is in the header now, which is where people look for it.
    const { container } = render(
      <Landing
        createForm={<p>Formular</p>}
        mapPicker={<p>Karte</p>}
        onOpen={vi.fn()}
        busy={false}
        loadStats={async () => null}
      />,
    );
    expect(container.querySelectorAll('.landing__way')).toHaveLength(2);
  });
});
