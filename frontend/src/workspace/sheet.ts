/*
 * The details as a sheet from below on a narrow window (doc 91): its three
 * heights, and where a drag of its handle comes to rest. Pure, and tested
 * without a layout.
 */

export type Snap = 'peek' | 'half' | 'full';

/** Lowest first. */
export const SNAPS: readonly Snap[] = ['peek', 'half', 'full'];

/** How much of the space between the header and the year's strip each height takes. */
export const SNAP_FRACTION: Readonly<Record<Snap, number>> = { peek: 0.25, half: 0.6, full: 0.9 };

/** Each height in words, for the handle's value. */
export const SNAP_WORDS: Readonly<Record<Snap, string>> = {
  peek: 'ein Viertel',
  half: 'gut die Hälfte',
  full: 'fast ganz',
};

/** A drag at least this fast, in spaces per second, is a flick. */
export const FLICK = 1.2;

const at = (index: number): Snap => SNAPS[Math.min(Math.max(index, 0), SNAPS.length - 1)] ?? 'peek';

/** One height up, or the top. */
export function raised(snap: Snap): Snap {
  return at(SNAPS.indexOf(snap) + 1);
}

/** One height down, or the bottom. */
export function lowered(snap: Snap): Snap {
  return at(SNAPS.indexOf(snap) - 1);
}

/** The height a drag has reached: where it started, moved by the finger's
 *  travel. Up grows the sheet. With no space to measure it stays put. */
export function dragFraction(start: number, startY: number, y: number, space: number): number {
  if (!(space > 0)) return start;
  return Math.min(Math.max(start + (startY - y) / space, 0), 1);
}

/** Where a released drag comes to rest: the next height the way a flick went,
 *  or else the nearest one. */
export function restingSnap(fraction: number, velocity: number): Snap {
  if (velocity >= FLICK) return SNAPS.find((snap) => SNAP_FRACTION[snap] > fraction) ?? 'full';
  if (velocity <= -FLICK) {
    return [...SNAPS].reverse().find((snap) => SNAP_FRACTION[snap] < fraction) ?? 'peek';
  }
  return SNAPS.reduce((nearest, snap) =>
    Math.abs(SNAP_FRACTION[snap] - fraction) < Math.abs(SNAP_FRACTION[nearest] - fraction) ? snap : nearest,
  );
}
