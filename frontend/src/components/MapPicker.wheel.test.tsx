import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { MapPicker } from './MapPicker';

const ORTE = [{ name: 'Am Weinberg, Kleinmachnow', lat: 52.4055, lon: 13.21 }];

async function shown(): Promise<HTMLElement> {
  render(
    <MapPicker onCreate={vi.fn()} busy={false} search={async () => ORTE}
               size={{ widthPx: 640, heightPx: 400 }} />,
  );
  fireEvent.change(screen.getByLabelText(/Adresse/), { target: { value: 'Weinberg' } });
  fireEvent.click(screen.getByRole('button', { name: /Such/ }));
  await waitFor(() => expect(screen.getByText(/Am Weinberg/)).toBeDefined());
  fireEvent.click(screen.getByRole('button', { name: /Am Weinberg/ }));
  return screen.getByTestId('map-surface');
}

/** The zoom levels of the tiles on show: …openstreetmap.org/{z}/{x}/{y}.png */
const levels = (surface: HTMLElement) => [
  ...new Set(
    [...surface.querySelectorAll('[data-testid="map-tiles"] img')].map(
      (img) => (img.getAttribute('src') ?? '').split('/')[3],
    ),
  ),
];

/** The owner's check, 2026-09-21, #4: the address map zooms with the wheel too. */
describe('MapPicker — the wheel', () => {
  it('steps one level in a notch, and takes the event', async () => {
    const surface = await shown();
    expect(levels(surface)).toEqual(['18']);
    const notCancelled = fireEvent.wheel(surface, { deltaY: 100 });
    expect(notCancelled).toBe(false);
    expect(levels(surface)).toEqual(['17']);
    fireEvent.wheel(surface, { deltaY: -100 });
    expect(levels(surface)).toEqual(['18']);
  });

  it('adds small trackpad steps up to a notch before it moves', async () => {
    const surface = await shown();
    for (let i = 0; i < 4; i += 1) fireEvent.wheel(surface, { deltaY: -20 });
    expect(levels(surface)).toEqual(['18']);
    fireEvent.wheel(surface, { deltaY: -20 });
    expect(levels(surface)).toEqual(['19']);
  });
});
