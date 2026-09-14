/*
 * Flowering months as the suggestion list shows them (doc 90): as cells, and
 * in words.
 */

export const MONTH_NAMES: readonly string[] = [
  'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
];

const isMonth = (value: number | null): value is number =>
  value !== null && Number.isInteger(value) && value >= 1 && value <= 12;

/**
 * The months a species flowers in, from its first to its last.
 *
 * A window that ends before it starts runs across the new year, as the server
 * reads it: doc 23 found 132 German species that a comparison of two numbers
 * dropped from the months they flower in.
 */
export function floweringMonths(start: number | null, end: number | null): number[] {
  if (!isMonth(start) || !isMonth(end)) return [];
  const months = [start];
  for (let month = start; month !== end; ) {
    month = (month % 12) + 1;
    months.push(month);
  }
  return months;
}

/** "Juni bis Juli", or "Mai" for a single month; empty when either end is unknown. */
export function monthSpan(start: number | null, end: number | null): string {
  if (!isMonth(start) || !isMonth(end)) return '';
  const first = MONTH_NAMES[start - 1] ?? '';
  return start === end ? first : `${first} bis ${MONTH_NAMES[end - 1] ?? ''}`;
}
