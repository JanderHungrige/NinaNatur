import { describe, expect, it } from 'vitest';

import { OVERSCAN, rowsPerPage, scrollToShow, visibleRange } from './window';

const ROW = 56;
const VIEW = 400;

describe('visibleRange — which rows a scroll position shows', () => {
  it('shows the rows in view and five either side, never before the first', () => {
    // 400 px of 56 px rows is rows 0–7; five more below make 13.
    expect(OVERSCAN).toBe(5);
    expect(visibleRange(0, VIEW, ROW, 50)).toEqual({ start: 0, end: 13 });
  });

  it('counts from the scroll position', () => {
    expect(visibleRange(ROW * 20, VIEW, ROW, 50)).toEqual({ start: 15, end: 33 });
  });

  it('never runs past the last row', () => {
    expect(visibleRange(ROW * 48, VIEW, ROW, 50)).toEqual({ start: 43, end: 50 });
  });

  it('keeps fewer than thirty of fifty rows in the document wherever the list is scrolled', () => {
    for (let top = 0; top <= ROW * 50; top += 37) {
      const { start, end } = visibleRange(top, VIEW, ROW, 50);
      expect(end - start).toBeLessThan(30);
      expect(end).toBeGreaterThan(start);
    }
  });

  it('renders nothing for an empty list', () => {
    expect(visibleRange(0, VIEW, ROW, 0)).toEqual({ start: 0, end: 0 });
  });
});

describe('scrollToShow — where to scroll so a row is in view', () => {
  it('scrolls down just far enough to show a row below the window', () => {
    expect(scrollToShow(20, 0, VIEW, ROW)).toBe(ROW * 21 - VIEW);
  });

  it('scrolls up to a row above the window', () => {
    expect(scrollToShow(3, 1000, VIEW, ROW)).toBe(ROW * 3);
  });

  it('leaves the scroll alone for a row already in view', () => {
    expect(scrollToShow(2, 0, VIEW, ROW)).toBe(0);
    expect(scrollToShow(22, ROW * 20, VIEW, ROW)).toBe(ROW * 20);
  });

  it('shows the top of a row that is taller than the window', () => {
    expect(scrollToShow(4, 0, 30, ROW)).toBe(ROW * 4);
  });
});

describe('rowsPerPage — the step of Page Up and Page Down', () => {
  it('counts the whole rows a window holds', () => {
    expect(rowsPerPage(VIEW, ROW)).toBe(7);
  });

  it('still moves when the window is lower than one row', () => {
    expect(rowsPerPage(30, ROW)).toBe(1);
  });
});
