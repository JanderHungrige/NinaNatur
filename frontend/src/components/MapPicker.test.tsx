import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { MapPicker } from './MapPicker';

const ORTE = [{ name: 'Am Weinberg, Kleinmachnow', lat: 52.4055, lon: 13.21 }];

function show(props: Partial<Parameters<typeof MapPicker>[0]> = {}) {
  const onCreate = vi.fn();
  render(
    <MapPicker
      onCreate={onCreate}
      busy={false}
      search={async () => ORTE}
      size={{ widthPx: 640, heightPx: 400 }}
      {...props}
    />,
  );
  return onCreate;
}

async function findPlace() {
  fireEvent.change(screen.getByLabelText(/Adresse/), { target: { value: 'Weinberg' } });
  fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));
  await waitFor(() => expect(screen.getByText(/Am Weinberg/)).toBeDefined());
  fireEvent.click(screen.getByRole('button', { name: /Am Weinberg/ }));
}

describe('MapPicker', () => {
  it('credits OpenStreetMap wherever the map is shown', () => {
    // Required by the licence and named again by the tile usage policy. It is a
    // condition of use, not a footer we may drop.
    show();
    expect(screen.getByText(/OpenStreetMap/)).toBeDefined();
  });

  it('does not search on every keystroke', async () => {
    // Nominatim is a free community service; a request per letter is how one
    // gets blocked, deservedly.
    const search = vi.fn(async () => ORTE);
    show({ search });
    fireEvent.change(screen.getByLabelText(/Adresse/), { target: { value: 'Wein' } });
    fireEvent.change(screen.getByLabelText(/Adresse/), { target: { value: 'Weinb' } });
    expect(search).not.toHaveBeenCalled();
  });

  it('searches when asked', async () => {
    const search = vi.fn(async () => ORTE);
    show({ search });
    fireEvent.change(screen.getByLabelText(/Adresse/), { target: { value: 'Weinberg' } });
    fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));
    await waitFor(() => expect(search).toHaveBeenCalledWith('Weinberg'));
  });

  it('says so when an address finds nothing', async () => {
    show({ search: async () => [] });
    fireEvent.change(screen.getByLabelText(/Adresse/), { target: { value: 'xyz' } });
    fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));
    await waitFor(() => expect(screen.getByText(/nichts gefunden/i)).toBeDefined());
  });

  it('shows the map once a place is chosen', async () => {
    show();
    await findPlace();
    expect(screen.getByTestId('map-tiles')).toBeDefined();
  });

  it('collects the outline as latitude and longitude', async () => {
    const onCreate = show();
    await findPlace();
    const surface = screen.getByTestId('map-surface');
    for (const [x, y] of [[300, 200], [340, 200], [340, 240], [300, 240]]) {
      fireEvent.click(surface, { clientX: x, clientY: y });
    }
    fireEvent.click(screen.getByRole('button', { name: 'Garten anlegen' }));
    const call = onCreate.mock.calls[0]?.[0];
    expect(call.outline).toHaveLength(4);
    expect(call.outline[0].lat).toBeCloseTo(52.4055, 2);
  });

  it('refuses an outline that is not an area', async () => {
    const onCreate = show();
    await findPlace();
    fireEvent.click(screen.getByTestId('map-surface'), { clientX: 300, clientY: 200 });
    fireEvent.click(screen.getByRole('button', { name: 'Garten anlegen' }));
    expect(onCreate).not.toHaveBeenCalled();
    expect(screen.getByText(/mindestens drei/i)).toBeDefined();
  });

  it('asks once what the neighbourhood looks like', async () => {
    // 75-88% of German suburban buildings carry no height in OSM. One question
    // per garden, not thirteen confirmations before the first suggestion.
    const onCreate = show();
    await findPlace();
    fireEvent.change(screen.getByLabelText(/Nachbarbebauung/), { target: { value: 'apartment' } });
    const surface = screen.getByTestId('map-surface');
    for (const [x, y] of [[300, 200], [340, 200], [340, 240]]) {
      fireEvent.click(surface, { clientX: x, clientY: y });
    }
    fireEvent.click(screen.getByRole('button', { name: 'Garten anlegen' }));
    expect(onCreate.mock.calls[0]?.[0].neighbourhood).toBe('apartment');
  });

  it('undoes the last corner', async () => {
    show();
    await findPlace();
    const surface = screen.getByTestId('map-surface');
    fireEvent.click(surface, { clientX: 300, clientY: 200 });
    fireEvent.click(surface, { clientX: 340, clientY: 200 });
    fireEvent.click(screen.getByRole('button', { name: 'Rückgängig' }));
    expect(screen.getByText(/1 Punkt\b/)).toBeDefined();
  });

  it('says what the margin is for', async () => {
    // The margin is the point of the whole feature, and it is invisible.
    show();
    await findPlace();
    expect(screen.getByText(/50 m/)).toBeDefined();
  });
});

describe('MapPicker — aerial imagery', () => {
  const BB = {
    url: 'https://isk.geobasis-bb.de/mapproxy/dop20c/service/wms',
    layer: 'bebb_dop20c',
    attribution: '© GeoBasis-DE/LGB, dl-de/by-2-0',
  };

  it('offers no aerial view where none is licensed', async () => {
    // Per Bundesland, because the licences are. A state without an entry gets
    // no imagery rather than a neighbour's.
    show({ findImagery: async () => null });
    await findPlace();
    expect(screen.queryByLabelText(/Luftbild/)).toBeNull();
  });

  it('offers it where one is, and names the source in the label', async () => {
    show({ findImagery: async () => BB });
    await findPlace();
    await waitFor(() => expect(screen.getByLabelText(/Luftbild/)).toBeDefined());
    expect(screen.getByText(/GeoBasis-DE\/LGB/)).toBeDefined();
  });

  it('credits the imagery whenever the imagery is shown', async () => {
    // DL-DE/BY and CC-BY both require the named credit; a photo without it is a
    // photo used outside its licence.
    show({ findImagery: async () => BB });
    await findPlace();
    await waitFor(() => expect(screen.getByLabelText(/Luftbild/)).toBeDefined());
    fireEvent.click(screen.getByLabelText(/Luftbild/));
    expect(screen.getByTestId('map-aerial')).toBeDefined();
    // In the attribution line specifically — the toggle names the source too,
    // and only the attribution line is the licence condition being met.
    const credit = document.querySelector('.map-picker__attribution');
    expect(credit?.textContent).toContain('dl-de/by-2-0');
  });

  it('goes back to the map when switched off', async () => {
    show({ findImagery: async () => BB });
    await findPlace();
    await waitFor(() => expect(screen.getByLabelText(/Luftbild/)).toBeDefined());
    fireEvent.click(screen.getByLabelText(/Luftbild/));
    fireEvent.click(screen.getByLabelText(/Luftbild/));
    expect(screen.getByTestId('map-tiles')).toBeDefined();
  });
});
