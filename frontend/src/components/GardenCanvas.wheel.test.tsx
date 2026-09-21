import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { GardenCanvas } from './GardenCanvas';

function garden(): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {},
    share_token: 'tok', name: 'Testgarten', latitude: 52.5, longitude: 13.4,
    created_at: '', updated_at: '', beds: [], obstacles: [],
  };
}

function mounted(): SVGSVGElement {
  render(
    <GardenCanvas garden={garden()} selectedBedId={null} onSelectBed={vi.fn()}
                  size={{ widthPx: 800, heightPx: 600 }} onDrawBed={vi.fn()} />,
  );
  return screen.getByTestId('canvas-surface') as unknown as SVGSVGElement;
}

/** The viewBox as numbers: x, y, width and height, in metres. */
const box = (svg: SVGSVGElement): number[] =>
  (svg.getAttribute('viewBox') ?? '').split(' ').map(Number);

/** The garden point under a pixel of the 800 × 600 surface. */
function under(svg: SVGSVGElement, px: number, py: number): [number, number] {
  const [x = 0, y = 0, w = 1, h = 1] = box(svg);
  return [x + (px / 800) * w, y + (py / 600) * h];
}

/**
 * Wheel zoom (the owner's check, 2026-09-21, #4). fireEvent rather than
 * dispatchEvent: a state update from a listener added outside React is not
 * flushed before the next line otherwise. Its return value is false when the
 * handler called preventDefault.
 */
describe('GardenCanvas — the wheel zooms', () => {
  afterEach(() => vi.useRealTimers());

  it('zooms on a plain wheel, and takes the event', () => {
    const svg = mounted();
    const before = box(svg)[2]!;
    const notCancelled = fireEvent.wheel(svg, { deltaY: -100, clientX: 400, clientY: 300 });
    expect(notCancelled).toBe(false);
    expect(box(svg)[2]!).toBeLessThan(before);
  });

  it('zooms out on a wheel turned the other way', () => {
    const svg = mounted();
    const before = box(svg)[2]!;
    fireEvent.wheel(svg, { deltaY: 100, clientX: 400, clientY: 300 });
    expect(box(svg)[2]!).toBeGreaterThan(before);
  });

  it('keeps the point under the pointer where it was', () => {
    const svg = mounted();
    const before = under(svg, 600, 150);
    fireEvent.wheel(svg, { deltaY: -100, clientX: 600, clientY: 150 });
    const after = under(svg, 600, 150);
    expect(after[0]).toBeCloseTo(before[0], 6);
    expect(after[1]).toBeCloseTo(before[1], 6);
  });

  it('moves a notch by a step, not to the limit', () => {
    const svg = mounted();
    const before = box(svg)[2]!;
    fireEvent.wheel(svg, { deltaY: -100 });
    const ratio = before / box(svg)[2]!;
    expect(ratio).toBeGreaterThan(1.1);
    expect(ratio).toBeLessThan(1.5);
  });

  it('follows a trackpad pinch in small steps', () => {
    // A pinch is dozens of tiny ctrl-wheel events a second. At a fixed 1.6 an
    // event, it slammed the view to its limit at once.
    const svg = mounted();
    const before = box(svg)[2]!;
    fireEvent.wheel(svg, { deltaY: 2, ctrlKey: true });
    const ratio = box(svg)[2]! / before;
    expect(ratio).toBeGreaterThan(1);
    expect(ratio).toBeLessThan(1.05);
  });

  it('reads a wheel that counts in lines as the pixels it means', () => {
    const lines = mounted();
    fireEvent.wheel(lines, { deltaY: -3, deltaMode: 1 });
    const byLines = box(lines)[2]!;
    document.body.innerHTML = '';
    const pixels = mounted();
    fireEvent.wheel(pixels, { deltaY: -48 });
    expect(byLines).toBeCloseTo(box(pixels)[2]!, 6);
  });

  it('never moves further than a doubling on one event', () => {
    const svg = mounted();
    const before = box(svg)[2]!;
    fireEvent.wheel(svg, { deltaY: 10000 });
    expect(box(svg)[2]! / before).toBeCloseTo(2, 6);
  });

  it("follows Safari's own pinch", () => {
    const svg = mounted();
    const before = box(svg)[2]!;
    const pinch = (type: string, scale: number) => {
      const event = Object.assign(new Event(type, { cancelable: true }),
        { scale, clientX: 400, clientY: 300 });
      act(() => { svg.dispatchEvent(event); });
      return event;
    };
    pinch('gesturestart', 1);
    const spread = pinch('gesturechange', 2);
    expect(spread.defaultPrevented).toBe(true);
    expect(box(svg)[2]!).toBeCloseTo(before / 2, 6);
  });

  it('pauses the costly paint while it turns, and brings it back after', () => {
    vi.useFakeTimers();
    const svg = mounted();
    fireEvent.wheel(svg, { deltaY: -100 });
    expect(svg.classList.contains('canvas--moving')).toBe(true);
    act(() => { vi.advanceTimersByTime(200); });
    expect(svg.classList.contains('canvas--moving')).toBe(false);
  });
});
