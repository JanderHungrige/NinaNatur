import { wobble, wobbleLine } from '../../canvas/sketch';
import type { Point } from '../../canvas/viewport';
import type { Wave } from './overlays';

/*
 * SVG path data for his marks (docs 97, 98): garden metres in, the plan's own
 * coordinates out (y flipped), to the millimetre.
 */

/** To the millimetre: a plan needs no finer, and a long street's path stays short. */
export const mm = (value: number): string => String(Math.round(value * 1000) / 1000);

const at = (p: Point): string => `${mm(p.x)},${mm(-p.y)}`;

export function ring(points: Point[]): string {
  return points.length === 0 ? '' : `M${points.map(at).join('L')}Z`;
}

export function polyline(points: Point[]): string {
  return points.length === 0 ? '' : `M${points.map(at).join('L')}`;
}

const middle = (a: Point, b: Point): Point => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });

/** A wavering line as a pen draws it: curves through the midpoints, no corners. */
function smoothRing(points: Point[]): string {
  const last = points[points.length - 1]!;
  const curves = points.map((p, i) => `Q${at(p)} ${at(middle(p, points[(i + 1) % points.length]!))}`);
  return `M${at(middle(last, points[0]!))}${curves.join('')}Z`;
}

function smoothLine(points: Point[]): string {
  const curves = points.slice(1, -1).map((p, i) => `Q${at(p)} ${at(middle(p, points[i + 2]!))}`);
  return `M${at(points[0]!)}${curves.join('')}L${at(points[points.length - 1]!)}`;
}

/** A wave that would not move the line by a pixel is not drawn: it could not
 *  be seen, and a curve every few centimetres round a hundred shapes is most of
 *  what the plan costs to draw. Nor is one sampled more finely than every
 *  few pixels, for the same reason. */
const SAMPLE_PX = 3;
const visible = (wave: Wave | null, metresPerPixel: number): wave is Wave =>
  wave !== null && wave.amplitude >= metresPerPixel;

/** An outline as his wave draws it. */
export function outline(points: Point[], wave: Wave | null, metresPerPixel: number): string {
  if (!visible(wave, metresPerPixel) || points.length < 3) return ring(points);
  return smoothRing(wobble(points, wave.amplitude, wave.period, wave.seed,
    SAMPLE_PX * metresPerPixel));
}

/** An open line as his wave draws it. */
export function stroke(points: Point[], wave: Wave | null, metresPerPixel: number): string {
  if (!visible(wave, metresPerPixel) || points.length < 2) return polyline(points);
  const drawn = wobbleLine(points, wave.amplitude, wave.period, wave.seed,
    SAMPLE_PX * metresPerPixel);
  return drawn.length < 3 ? polyline(drawn) : smoothLine(drawn);
}

/** His line at 1:250 is a hair at 1:2,000; it never gets thinner than a pixel. */
export const width = (metres: number, metresPerPixel: number): string =>
  mm(Math.max(metres, metresPerPixel));
