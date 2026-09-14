/*
 * The arithmetic of a list that shows a window of its rows (doc 90). Every size
 * is handed in, so it is tested without a layout — jsdom does not lay out.
 */

/** Rows kept in the document above and below the ones in view. */
export const OVERSCAN = 5;

/** A run of rows, from `start` up to but not including `end`. */
export interface RowRange {
  start: number;
  end: number;
}

const clamp = (value: number, low: number, high: number): number =>
  Math.min(Math.max(value, low), high);

/** Which rows a scroll position shows, with the overscan either side. */
export function visibleRange(top: number, viewport: number, row: number, count: number): RowRange {
  if (count <= 0) return { start: 0, end: 0 };
  const size = Math.max(row, 1);
  const from = Math.max(top, 0);
  const first = Math.floor(from / size);
  const last = Math.ceil((from + Math.max(viewport, 0)) / size);
  return {
    start: clamp(first - OVERSCAN, 0, count - 1),
    end: clamp(last + OVERSCAN, 1, count),
  };
}

/** Where to scroll so row `index` is in view, moving as little as possible. A
 *  row taller than the window is shown from its top. */
export function scrollToShow(index: number, top: number, viewport: number, row: number): number {
  const rowTop = index * row;
  const rowBottom = rowTop + row;
  if (rowTop < top) return rowTop;
  if (rowBottom > top + viewport) return Math.min(rowTop, rowBottom - viewport);
  return top;
}

/** How many whole rows a window holds: how far Page Up and Page Down move. */
export function rowsPerPage(viewport: number, row: number): number {
  return Math.max(1, Math.floor(viewport / Math.max(row, 1)));
}
