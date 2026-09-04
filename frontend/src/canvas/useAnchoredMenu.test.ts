import { describe, expect, it } from 'vitest';

import { fit } from './useAnchoredMenu';

const VIEW = { width: 1000, height: 800 };
const MENU = { width: 240, height: 300 };

function anchor(left: number, top: number, width = 100, height = 80) {
  return { left, top, right: left + width, bottom: top + height };
}

describe('fit — where a menu about a shape belongs', () => {
  it('sits under the shape when there is room', () => {
    const { top, left } = fit(anchor(200, 100), MENU, VIEW);
    expect(top).toBe(100 + 80 + 6);
    expect(left).toBe(200);
  });

  it('flips above the shape rather than off the bottom', () => {
    // The reported bug. A shape low in the window used to put half the menu
    // below the fold, and because it was `position: fixed` scrolling could not
    // reach it.
    const { top } = fit(anchor(200, 700), MENU, VIEW);

    expect(top).toBe(700 - 300 - 6);
    expect(top).toBeGreaterThanOrEqual(8);
  });

  it('never leaves the window even when neither side fits', () => {
    // A tall shape in a short window: no room below, none above.
    const { top } = fit(anchor(200, 40, 100, 700), { width: 240, height: 300 }, VIEW);

    expect(top).toBeGreaterThanOrEqual(8);
    expect(top + 300).toBeLessThanOrEqual(800 - 8 + 0.001);
  });

  it('pulls back from the right edge', () => {
    const { left } = fit(anchor(950, 100), MENU, VIEW);
    expect(left).toBe(1000 - 240 - 8);
  });

  it('stays clear of the left edge', () => {
    const { left } = fit(anchor(-40, 100), MENU, VIEW);
    expect(left).toBe(8);
  });

  it('pins to the top when the menu is taller than the window', () => {
    // Not hypothetical: the kind menu on a small laptop with the browser's
    // font size raised. Clamping the other way would put the heading and the
    // close button above the top edge — the two things most needed.
    const { top } = fit(anchor(200, 300), { width: 240, height: 900 }, VIEW);
    expect(top).toBe(8);
  });
});
