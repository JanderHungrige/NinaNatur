/**
 * Flowers in a bed, as dots rather than as a bar.
 *
 * A colour bar says the bed is half yellow and half blue. What is true is that
 * some of the flowers are yellow and some are blue — and that the yellow ones
 * are together, because nobody plants one salvia here and one over there.
 *
 * A tiling pattern cannot say that: a pattern repeats uniformly and clustering
 * is the opposite of uniform. So the positions are generated, and seeded from
 * the bed's own id — without that the planting reshuffles on every render,
 * which reads as the garden twitching.
 */
import { covers } from './geometry';
import type { Point } from './viewport';

export interface BloomDot {
  x: number;
  y: number;
  colour: string;
  /** Metres. Varied, because flowers are not one size. */
  r: number;
}

/**
 * Past this, more dots carry no more meaning and cost a node each. A bed with
 * two hundred plants is not two hundred dots; it is a bed that reads as full.
 */
export const MAX_DOTS = 90;

/** One dot per this much ground, before the cap. */
const SQUARE_METRES_PER_DOT = 0.55;

/** Deterministic, and cheap: mulberry32 on the bed id. */
function random(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4_294_967_296;
  };
}

function bounds(polygon: number[][]) {
  const xs = polygon.map((p) => p[0] ?? 0);
  const ys = polygon.map((p) => p[1] ?? 0);
  return {
    minX: Math.min(...xs), maxX: Math.max(...xs),
    minY: Math.min(...ys), maxY: Math.max(...ys),
  };
}

/** Shoelace. The bed's own area, not its bounding box. */
function area(polygon: number[][]): number {
  let sum = 0;
  for (let i = 0; i < polygon.length; i += 1) {
    const a = polygon[i]!;
    const b = polygon[(i + 1) % polygon.length]!;
    sum += a[0]! * b[1]! - b[0]! * a[1]!;
  }
  return Math.abs(sum) / 2;
}

/** A point inside the bed, or null after a fair number of tries. */
function somewhereInside(
  polygon: Point[],
  box: ReturnType<typeof bounds>,
  next: () => number,
): { x: number; y: number } | null {
  // Rejection sampling: an L-shaped bed's notch is not in the bed, and a
  // bounding-box guess would put flowers in it.
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const at = {
      x: box.minX + next() * (box.maxX - box.minX),
      y: box.minY + next() * (box.maxY - box.minY),
    };
    if (covers(polygon, at)) return at;
  }
  return null;
}

export function bloomDots(
  bedId: number,
  outline: number[][],
  colours: string[],
): BloomDot[] {
  if (colours.length === 0 || outline.length < 3) return [];

  const polygon: Point[] = outline.map((p) => ({ x: p[0] ?? 0, y: p[1] ?? 0 }));
  const next = random(bedId * 2654435761);
  const box = bounds(outline);
  const wanted = Math.min(
    MAX_DOTS,
    Math.max(colours.length * 3, Math.round(area(outline) / SQUARE_METRES_PER_DOT)),
  );
  const perColour = Math.max(2, Math.floor(wanted / colours.length));
  const spread = Math.min(box.maxX - box.minX, box.maxY - box.minY) / 4;

  const dots: BloomDot[] = [];
  for (const colour of colours) {
    // One centre per colour, and its flowers around it — the drift is what
    // makes a group read as planted rather than as a stamp.
    const centre = somewhereInside(polygon, box, next);
    if (centre === null) continue;
    for (let i = 0; i < perColour && dots.length < MAX_DOTS; i += 1) {
      const angle = next() * Math.PI * 2;
      // sqrt keeps the group even rather than crowding its middle.
      const distance = Math.sqrt(next()) * spread;
      const at = {
        x: centre.x + Math.cos(angle) * distance,
        y: centre.y + Math.sin(angle) * distance,
      };
      if (!covers(polygon, at)) continue;
      dots.push({
        x: Math.round(at.x * 100) / 100,
        y: Math.round(at.y * 100) / 100,
        colour,
        // Flowers are not one size, and a field of identical circles is the
        // same mistake the motes made on the landing page.
        r: Math.round((0.12 + next() * 0.13) * 100) / 100,
      });
    }
  }
  return dots;
}
