import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { MapPicker } from './MapPicker';

/* The owner's check (2026-09-21): the front door says what it waits for. */

const ORTE = [{ name: 'Am Weinberg, Kleinmachnow', lat: 52.4055, lon: 13.21 }];

function show(props: Partial<Parameters<typeof MapPicker>[0]> = {}) {
  render(
    <MapPicker
      onCreate={vi.fn()}
      busy={false}
      search={async () => ORTE}
      size={{ widthPx: 640, heightPx: 400 }}
      {...props}
    />,
  );
}

describe('MapPicker — saying what it waits for', () => {
  it('says it is searching while the address service answers', async () => {
    // Nominatim is a free service and answers when it can; a button that only
    // greys out looks like a click that did nothing.
    let answer: (places: typeof ORTE) => void = () => undefined;
    show({ search: () => new Promise((resolve) => { answer = resolve; }) });
    fireEvent.change(screen.getByLabelText(/Adresse/), { target: { value: 'Weinberg' } });
    fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));
    const searching = screen.getByRole('button', { name: 'Suche…' }) as HTMLButtonElement;
    expect(searching.disabled).toBe(true);
    expect(searching.querySelector('.working__spinner')?.getAttribute('aria-hidden')).toBe('true');

    answer(ORTE);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Suchen' })).toBeDefined());
  });

  it('says the garden is being made, and with what, until it is', async () => {
    // The server asks OpenStreetMap for every building and street first:
    // seconds, not a blink.
    let done: () => void = () => undefined;
    const onCreate = vi.fn(() => new Promise<void>((resolve) => { done = resolve; }));
    show({ onCreate });
    fireEvent.change(screen.getByLabelText(/Adresse/), { target: { value: 'Weinberg' } });
    fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));
    fireEvent.click(await screen.findByRole('button', { name: /Am Weinberg/ }));
    const surface = screen.getByTestId('map-surface');
    for (const [x, y] of [[300, 200], [340, 200], [340, 240]]) {
      fireEvent.click(surface, { clientX: x, clientY: y });
    }
    fireEvent.click(screen.getByRole('button', { name: 'Garten anlegen' }));
    expect(screen.getByRole('button', { name: 'Wird angelegt…' })).toBeDefined();
    expect(screen.getByText(/Gebäude und Straßen aus OpenStreetMap werden übernommen/)).toBeDefined();

    done();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Garten anlegen' })).toBeDefined());
    expect(screen.queryByText(/werden übernommen/)).toBeNull();
  });
});
