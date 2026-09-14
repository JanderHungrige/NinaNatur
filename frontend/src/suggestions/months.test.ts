import { describe, expect, it } from 'vitest';

import { floweringMonths, monthSpan } from './months';

describe('floweringMonths — a flowering window as months', () => {
  it('lists the months from start to end', () => {
    expect(floweringMonths(6, 7)).toEqual([6, 7]);
  });

  it('wraps across the new year, as the server does', () => {
    // Doc 23: 132 German species flower across December and January, and a
    // comparison of two integers lost every one of them.
    expect(floweringMonths(12, 7)).toEqual([12, 1, 2, 3, 4, 5, 6, 7]);
  });

  it('is one month when start and end agree', () => {
    expect(floweringMonths(5, 5)).toEqual([5]);
  });

  it('is nothing when either end is unknown', () => {
    expect(floweringMonths(null, 7)).toEqual([]);
    expect(floweringMonths(6, null)).toEqual([]);
  });
});

describe('monthSpan — the same window in words', () => {
  it('names the first and the last month', () => {
    expect(monthSpan(6, 7)).toBe('Juni bis Juli');
    expect(monthSpan(12, 7)).toBe('Dezember bis Juli');
  });

  it('names a single month once', () => {
    expect(monthSpan(5, 5)).toBe('Mai');
  });

  it('says nothing it does not know', () => {
    expect(monthSpan(null, null)).toBe('');
  });
});
