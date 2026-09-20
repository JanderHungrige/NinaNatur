/**
 * Provenance: NinaNatur, in the style of Draft Sketch
 *
 * What his style has no symbol for, drawn in his manner (doc 98): his black
 * ink, his wobble, his light from the upper left and his shadows falling to the
 * lower right. Ours, not his — this header says so, and the provenance test
 * holds every rules file to its header. Metres, as his generated rules are.
 */
import type { Overlay } from '../overlays';

const INK = { colour: '#000000', opacity: 1 } as const;
/** His shadows fall this way: away from a light in the upper left. */
const SHADE = { x: 1, y: -1 } as const;

/** A roof's ridge, hips or upper edge, from the server's roof model: a line
 *  inside the outline, so thinner than it. */
export const ROOF: readonly Overlay[] = [
  { kind: 'roof', ...INK, width: 0.07, wave: { amplitude: 0.035, period: 0.9, seed: 5 } },
];

/** A raised bed: its side's shadow, and a second edge just inside the first
 *  where the board's top is. */
export const RAISED: readonly Overlay[] = [
  // The bed's own side, not a shadow the sun throws: it stays where it is drawn.
  { kind: 'shadow', colour: '#000000', opacity: 0.2, dx: 0.18, dy: -0.18, wave: null,
    edge: true },
  { kind: 'inner', ...INK, width: 0.06, inset: 0.18, wave: { amplitude: 0.03, period: 0.8, seed: 9 } },
];

/** A hedge is clipped: a mass with a shaded side, hatched along it. */
export const HEDGE: readonly Overlay[] = [
  { kind: 'ticks', ...INK, width: 0.035, length: 0.35, spacing: 0.25, inset: 0.2, angle: 60,
    facing: SHADE },
];
