/**
 * Saying how the ground falls, in the words a gardener uses.
 *
 * The server sends degrees and a compass bearing; nobody stands in their garden
 * and thinks in bearings. "Südhang, 9 %" is the sentence — a direction anybody
 * can picture and a gradient in the units paths and ramps are measured in.
 *
 * **Named, never scored.** Wave 17 measured what a slope does to the sun hours
 * at this latitude and the answer was: almost nothing. A 17° slope moves them
 * by a fifth of an hour, because the noon sun runs from 38° to 61° over the
 * season and clears a 17° skyline easily. What a north bank really loses is
 * energy per square metre, which this model does not compute — so the slope is
 * put in front of the gardener as a fact about their garden rather than folded
 * into a light figure that would then be quietly wrong.
 */

/** The eight points, and the German word for each. */
const POINTS: ReadonlyArray<readonly [number, string]> = [
  [0, 'Nordhang'],
  [45, 'Nordosthang'],
  [90, 'Osthang'],
  [135, 'Südosthang'],
  [180, 'Südhang'],
  [225, 'Südwesthang'],
  [270, 'Westhang'],
  [315, 'Nordwesthang'],
];

/** Below this the ground is level enough not to be worth a word. */
export const FLAT_BELOW_DEG = 2;

/** The compass word for a bearing, or null when there is nothing to say. */
export function slopeName(aspectDeg: number | null): string | null {
  if (aspectDeg === null || !Number.isFinite(aspectDeg)) return null;
  const bearing = ((aspectDeg % 360) + 360) % 360;
  const point = POINTS[Math.round(bearing / 45) % POINTS.length];
  // `noUncheckedIndexedAccess` is on, and it is right to be: 359.9° rounds to
  // index 8, which is one past the end before the modulo brings it home.
  return point === undefined ? null : point[1];
}

/** A slope in per cent, the way a ramp or a path is measured. */
export function slopePercent(slopeDeg: number): number {
  return Math.round(Math.tan((slopeDeg * Math.PI) / 180) * 100);
}

/**
 * The whole sentence, or null for ground that is level — or unmeasured.
 *
 * Level and unmeasured are deliberately different: `null` slope means nobody
 * has fetched the ground, and saying "eben" about a garden nobody has looked at
 * would be the same false confidence the flat model had all along.
 */
export function slopeSentence(
  slopeDeg: number | null,
  aspectDeg: number | null,
): string | null {
  if (slopeDeg === null || !Number.isFinite(slopeDeg)) return null;
  if (slopeDeg < FLAT_BELOW_DEG) return 'eben';
  const name = slopeName(aspectDeg);
  const percent = slopePercent(slopeDeg);
  return name === null ? `${percent} % Gefälle` : `${name}, ${percent} %`;
}
