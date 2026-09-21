import { describe, expect, it } from 'vitest';

import { REFERENCE_MPP, inkWidth, onScreen, outline } from './paths';

/** The owner's check, 2026-09-21, #1: lines too thick to draw in detail. */
describe('his ink at every zoom', () => {
  it('draws his width as it is at his own scale', () => {
    expect(inkWidth(0.103, REFERENCE_MPP)).toBeCloseTo(0.103, 9);
  });

  it('never grows past his on-screen width when zoomed in', () => {
    // At the closest view (about 2 mm a pixel) it was 50 pixels wide.
    const mpp = 0.002;
    const pixels = inkWidth(0.103, mpp) / mpp;
    expect(pixels).toBeCloseTo(0.103 / REFERENCE_MPP, 6);
    expect(pixels).toBeLessThan(2);
  });

  it('thins as before when zoomed out, down to a pixel', () => {
    expect(inkWidth(0.103, 0.5)).toBe(0.5);
    expect(inkWidth(0.103, 0.08)).toBeCloseTo(0.103, 9);
  });

  it('caps a wave the same way, so a zoomed-in bed stays on its corners', () => {
    expect(onScreen(0.0882, 0.002) / 0.002).toBeLessThan(1.5);
    const square = [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }, { x: 0, y: 1 }];
    const wave = { amplitude: 0.0882, period: 0.6, seed: 3 };
    const drawn = outline(square, wave, 0.002);
    const numbers = [...drawn.matchAll(/-?\d+(\.\d+)?/g)].map((m) => Math.abs(Number(m[0])));
    // Every coordinate within a few pixels (a few millimetres) of the square.
    expect(Math.max(...numbers)).toBeLessThan(1.005);
  });
});
