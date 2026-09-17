import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { MapPicker } from './MapPicker';

/*
 * Doc 31, B1: the picker drew a map 640 px wide whatever the surface was, and
 * nothing measured it. On the preview at 375×635 the surface is 259 px: a tap in
 * the middle set a corner 77 px to its left, one at the right quarter 115 px
 * away, and the map could not be moved at all, because panning wanted the right
 * mouse button (2026-09-17).
 *
 * Every test in MapPicker.test.tsx passes `size`, which is how the suite stayed
 * green through all of it. These pass none: the surface is measured here, as it
 * is in a browser.
 */

const ORTE = [{ name: 'Am Weinberg, Kleinmachnow', lat: 52.4055, lon: 13.21 }];
const BB = {
  url: 'https://isk.geobasis-bb.de/mapproxy/dop20c/service/wms',
  layer: 'bebb_dop20c',
  attribution: '© GeoBasis-DE/LGB, dl-de/by-2-0',
};
/** What the preview measured on an iPhone 11 Pro. */
const PHONE = { width: 259, height: 400, left: 58, top: 117 };

/** jsdom lays nothing out, so the surface is told what it would be in a phone. */
class FakeObserver {
  static made: FakeObserver[] = [];
  private readonly callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    FakeObserver.made.push(this);
  }

  observe(): void {
    this.fire();
  }

  unobserve(): void {}

  disconnect(): void {}

  fire(): void {
    this.callback([], this as unknown as ResizeObserver);
  }
}

beforeEach(() => {
  FakeObserver.made = [];
  vi.stubGlobal('ResizeObserver', FakeObserver);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function show(props: Partial<Parameters<typeof MapPicker>[0]> = {}) {
  const onCreate = vi.fn();
  // No `size`: the picker has to find out how wide it is, as it must in a browser.
  render(<MapPicker onCreate={onCreate} busy={false} search={async () => ORTE} {...props} />);
  return onCreate;
}

async function findPlace() {
  fireEvent.change(screen.getByLabelText(/Adresse/), { target: { value: 'Weinberg' } });
  fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));
  await waitFor(() => expect(screen.getByText(/Am Weinberg/)).toBeDefined());
  fireEvent.click(screen.getByRole('button', { name: /Am Weinberg/ }));
}

/** The surface as a phone lays it out, measured again as a resize would. */
function asPhone(): HTMLElement {
  const surface = screen.getByTestId('map-surface');
  surface.getBoundingClientRect = () =>
    ({
      width: PHONE.width,
      height: PHONE.height,
      left: PHONE.left,
      top: PHONE.top,
      right: PHONE.left + PHONE.width,
      bottom: PHONE.top + PHONE.height,
      x: PHONE.left,
      y: PHONE.top,
      toJSON: () => ({}),
    }) as DOMRect;
  act(() => {
    for (const observer of FakeObserver.made) observer.fire();
  });
  return surface;
}

/** A tap at a place inside the surface, in the window's coordinates. */
const at = (x: number, y: number) => ({ clientX: PHONE.left + x, clientY: PHONE.top + y });

describe('MapPicker — the surface it really has', () => {
  it('projects a tap through the measured width, not through 640 px', async () => {
    const onCreate = show();
    await findPlace();
    const surface = asPhone();

    // The middle of the map is the place the map is centred on.
    for (let i = 0; i < 3; i += 1) fireEvent.click(surface, at(PHONE.width / 2, PHONE.height / 2));
    fireEvent.click(screen.getByRole('button', { name: 'Garten anlegen' }));

    const corner = onCreate.mock.calls[0]?.[0].outline[0];
    expect(corner.lon).toBeCloseTo(13.21, 4);
    expect(corner.lat).toBeCloseTo(52.4055, 4);
  });

  it('draws the corner where the finger was', async () => {
    show();
    await findPlace();
    const surface = asPhone();
    fireEvent.click(surface, at(40, 30));

    // One space, not two: the drawing scaled a 640-wide viewBox into 259 px.
    const outline = surface.querySelector('.map-picker__outline');
    expect(outline?.getAttribute('viewBox')).toBe(`0 0 ${PHONE.width} ${PHONE.height}`);
    const corner = surface.querySelector('circle');
    expect(Number(corner?.getAttribute('cx'))).toBeCloseTo(40, 0);
    expect(Number(corner?.getAttribute('cy'))).toBeCloseTo(30, 0);
  });

  it('asks for the tiles the surface can show and no others', async () => {
    // The tile policy forbids fetching more than the window needs (doc 31).
    show();
    await findPlace();
    const surface = asPhone();

    const lefts = [...surface.querySelectorAll('[data-testid="map-tiles"] img')].map((img) =>
      Number.parseFloat((img as HTMLElement).style.left),
    );
    expect(lefts.length).toBeGreaterThan(0);
    expect(Math.max(...lefts)).toBeLessThan(PHONE.width);
    expect(Math.min(...lefts)).toBeGreaterThan(-256);
  });

  it('asks for the aerial photo at the size it will be shown', async () => {
    show({ findImagery: async () => BB });
    await findPlace();
    asPhone();
    await waitFor(() => expect(screen.getByLabelText(/Luftbild/)).toBeDefined());
    fireEvent.click(screen.getByLabelText(/Luftbild/));

    const photo = screen.getByTestId('map-aerial');
    expect(photo.getAttribute('width')).toBe(String(PHONE.width));
    expect(photo.getAttribute('src')).toContain(`WIDTH=${PHONE.width}`);
  });
});

describe('MapPicker — a finger on the map', () => {
  /** Where the tiles sit, not only which they are: a drag shorter than a tile
   *  moves the same six images rather than fetching new ones. */
  const layout = (surface: HTMLElement) =>
    [...surface.querySelectorAll('[data-testid="map-tiles"] img')].map((img) => {
      const tile = img as HTMLElement;
      return `${img.getAttribute('src')} at ${tile.style.left},${tile.style.top}`;
    });

  it('drags the map, where a mouse needs its right button', async () => {
    show();
    await findPlace();
    const surface = asPhone();
    const before = layout(surface);

    fireEvent.pointerDown(surface, { pointerType: 'touch', button: 0, ...at(150, 250) });
    fireEvent.pointerMove(window, { pointerType: 'touch', ...at(90, 200) });
    fireEvent.pointerUp(window, { pointerType: 'touch', ...at(90, 200) });

    expect(layout(surface)).not.toEqual(before);
    expect(screen.getByText(/0 Punkte/)).toBeDefined();
  });

  it('sets a corner on a tap, and none after a drag', async () => {
    show();
    await findPlace();
    const surface = asPhone();

    // A tap: down and up within a few pixels, and the click the browser sends after.
    fireEvent.pointerDown(surface, { pointerType: 'touch', button: 0, ...at(150, 250) });
    fireEvent.pointerUp(window, { pointerType: 'touch', ...at(152, 251) });
    fireEvent.click(surface, at(152, 251));
    expect(screen.getByText(/1 Punkt\b/)).toBeDefined();

    // A drag: whatever click follows it belongs to the pan, not to a corner.
    fireEvent.pointerDown(surface, { pointerType: 'touch', button: 0, ...at(150, 250) });
    fireEvent.pointerMove(window, { pointerType: 'touch', ...at(90, 200) });
    fireEvent.pointerUp(window, { pointerType: 'touch', ...at(90, 200) });
    fireEvent.click(surface, at(90, 200));
    expect(screen.getByText(/1 Punkt\b/)).toBeDefined();
  });
});
