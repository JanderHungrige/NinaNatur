import { describe, expect, it } from 'vitest';

import { FLICK, SNAP_FRACTION, SNAPS, SNAP_WORDS, dragFraction, lowered, raised, restingSnap } from './sheet';

describe('the sheet’s heights', () => {
  it('are a quarter, 60 % and 90 %, lowest first', () => {
    // The wave's three heights (doc 91).
    expect(SNAPS).toEqual(['peek', 'half', 'full']);
    expect(SNAPS.map((snap) => SNAP_FRACTION[snap])).toEqual([0.25, 0.6, 0.9]);
  });

  it('are said in words', () => {
    expect(SNAPS.map((snap) => SNAP_WORDS[snap])).toEqual(['ein Viertel', 'gut die Hälfte', 'fast ganz']);
  });

  it('go up and down one at a time, and stop at the ends', () => {
    expect(raised('peek')).toBe('half');
    expect(raised('half')).toBe('full');
    expect(raised('full')).toBe('full');
    expect(lowered('full')).toBe('half');
    expect(lowered('half')).toBe('peek');
    expect(lowered('peek')).toBe('peek');
  });
});

describe('dragFraction — the height a drag has reached', () => {
  it('follows the finger: up grows the sheet, down shrinks it', () => {
    expect(dragFraction(0.25, 500, 300, 400)).toBeCloseTo(0.75);
    expect(dragFraction(0.6, 300, 420, 400)).toBeCloseTo(0.3);
  });

  it('never leaves the space it stands in', () => {
    expect(dragFraction(0.9, 300, 0, 400)).toBe(1);
    expect(dragFraction(0.25, 300, 800, 400)).toBe(0);
  });

  it('stays where it started when there is no space to measure', () => {
    // jsdom lays nothing out, and a hidden sheet measures nothing either.
    expect(dragFraction(0.6, 300, 100, 0)).toBe(0.6);
  });
});

describe('restingSnap — where a released drag comes to rest', () => {
  it('is the nearest height when the drag was slow', () => {
    expect(restingSnap(0.3, 0)).toBe('peek');
    expect(restingSnap(0.45, 0)).toBe('half');
    expect(restingSnap(0.8, FLICK / 2)).toBe('full');
  });

  it('is the next height the way a flick went', () => {
    expect(restingSnap(0.3, FLICK)).toBe('half');
    expect(restingSnap(0.62, FLICK)).toBe('full');
    expect(restingSnap(0.85, -FLICK)).toBe('half');
    expect(restingSnap(0.55, -FLICK)).toBe('peek');
  });

  it('stops at the ends however hard the flick', () => {
    expect(restingSnap(0.95, FLICK * 3)).toBe('full');
    expect(restingSnap(0.1, -FLICK * 3)).toBe('peek');
  });
});
