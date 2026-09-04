import { covers } from './geometry';
import type { Point } from './viewport';

/**
 * A patch of one species in one bed.
 *
 * Nobody plants one salvia here and one over there — a species goes in as a
 * group, and a plan that scatters it evenly says something untrue about the
 * garden. So each planting is one cluster, which is also what the table has
 * always said: `UNIQUE (element_id, taxon_id)`, one row per species per bed.
 *
 * The cluster carries the whole of the plan's answer to "how full is this bed":
 * every planting is drawn whether it is in flower or not, grey when it is not.
 * The colour band it replaces could only ever show the beds that were flowering
 * *now*, and an empty bed and a bed full of leaves looked the same.
 */
export interface Cluster {
  plantingId: number;
  taxonId: number | null;
  name: string;
  /** The middle, in absolute metres. */
  centre: Point;
  /** Metres. Soft-edged on purpose — see `radiusFor`. */
  radius: number;
  /** The bloom colour if it is in flower this month, else null for grey. */
  colour: string | null;
  dots: Dot[];
}

export interface Dot {
  x: number;
  y: number;
  r: number;
}

export interface PlantingLike {
  planting_id: number;
  taxon_id: number | null;
  canonical_name: string | null;
  raw_name: string | null;
  quantity: number;
  x: number | null;
  y: number | null;
}

export interface ColourLike {
  planting_id: number;
  colour: string | null;
  months: number[];
  space_m2: number | null;
}

/**
 * Ground one plant claims when the catalogue will not say.
 *
 * The catalogue records no spread at all: `space_m2` is estimated from a height
 * known for 3,952 of 8,939 species, so most clusters land here. A third of a
 * square metre is a perennial at a normal spacing — enough that ten of them
 * read as a patch, little enough that it does not swallow a small bed.
 */
export const DEFAULT_ROOM_M2 = 0.33;

/** Past this many, more dots say nothing further and cost a node each. */
export const MAX_DOTS = 40;
/**
 * How far inside the outline a clamped cluster is put, in metres.
 *
 * Larger than the centimetre a stored position is rounded to. See `keepInside`.
 */
export const INSET_M = 0.02;

/** No cluster smaller than this, or a single plant is a speck. */
const MIN_RADIUS_M = 0.22;

/**
 * How big a patch of `quantity` plants is, in metres.
 *
 * From the room they claim, which for most species is a guess and for the rest
 * is a rule of thumb derived from height. It sizes a soft blob and is never
 * printed: `canopy.py` states the rule this obeys — a derived number that looks
 * measured is worse than no number.
 */
export function radiusFor(quantity: number, spaceM2: number | null): number {
  const room = (spaceM2 ?? DEFAULT_ROOM_M2) * Math.max(1, quantity);
  return Math.max(MIN_RADIUS_M, Math.sqrt(room / Math.PI));
}

/** Deterministic and cheap: mulberry32. */
function random(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4_294_967_296;
  };
}

function bounds(polygon: Point[]) {
  const xs = polygon.map((p) => p.x);
  const ys = polygon.map((p) => p.y);
  return {
    minX: Math.min(...xs), maxX: Math.max(...xs),
    minY: Math.min(...ys), maxY: Math.max(...ys),
  };
}

/**
 * Where a cluster nobody has moved sits.
 *
 * Seeded from the planting id, so it is in the same place on every render and
 * in every browser — a patch that wanders between reloads reads as the garden
 * twitching. Rejection sampling against the outline rather than the bounding
 * box, because an L-shaped bed's notch is not in the bed.
 */
export function defaultCentre(plantingId: number, outline: Point[]): Point {
  const box = bounds(outline);
  const next = random(plantingId * 2654435761);
  for (let attempt = 0; attempt < 60; attempt += 1) {
    const at = {
      x: box.minX + next() * (box.maxX - box.minX),
      y: box.minY + next() * (box.maxY - box.minY),
    };
    if (covers(outline, at)) return at;
  }
  // A bed so thin that sixty guesses all missed. The centroid of the bounding
  // box is wrong in an L, and visible, which is better than not drawn at all.
  return { x: (box.minX + box.maxX) / 2, y: (box.minY + box.maxY) / 2 };
}

/** What to call a planting: the catalogue's name, or the gardener's own. */
export function nameOf(planting: PlantingLike): string {
  return planting.canonical_name ?? planting.raw_name ?? 'Unbenannt';
}

/**
 * The clusters of one bed, in the month being shown.
 *
 * `month` null means no month is being played — everything is drawn grey, which
 * is the honest reading of "what is in this bed" outside the bloom year.
 */
export function clustersFor(
  outline: number[][],
  plantings: PlantingLike[],
  colours: ColourLike[],
  month: number | null,
): Cluster[] {
  if (outline.length < 3) return [];
  const polygon: Point[] = outline.map((p) => ({ x: p[0] ?? 0, y: p[1] ?? 0 }));
  const byId = new Map(colours.map((c) => [c.planting_id, c]));

  return plantings.map((planting) => {
    const entry = byId.get(planting.planting_id);
    const centre =
      planting.x !== null && planting.y !== null
        ? { x: planting.x, y: planting.y }
        : defaultCentre(planting.planting_id, polygon);
    const radius = radiusFor(planting.quantity, entry?.space_m2 ?? null);
    const inFlower =
      month !== null && entry !== undefined && entry.months.includes(month);

    return {
      plantingId: planting.planting_id,
      taxonId: planting.taxon_id,
      name: nameOf(planting),
      centre,
      radius,
      colour: inFlower ? (entry?.colour ?? null) : null,
      dots: dotsIn(centre, radius, planting.quantity, planting.planting_id),
    };
  });
}

/**
 * The dots of one patch.
 *
 * Denser in the middle — `sqrt` of a uniform draw spreads points evenly over a
 * disc, and this deliberately does not: a patch of plants thins out at its
 * edges, and a disc of evenly scattered dots reads as a printed circle.
 */
export function dotsIn(
  centre: Point,
  radius: number,
  quantity: number,
  seed: number,
): Dot[] {
  const many = Math.max(1, Math.min(MAX_DOTS, quantity));
  const next = random(seed * 40503 + 7);
  const dots: Dot[] = [];
  for (let i = 0; i < many; i += 1) {
    const angle = next() * Math.PI * 2;
    const away = next() ** 0.85 * radius;
    dots.push({
      x: centre.x + Math.cos(angle) * away,
      y: centre.y + Math.sin(angle) * away,
      // Varied, because plants are not one size, and because a field of
      // identical circles is the thing that reads as a pattern.
      r: radius * (0.14 + next() * 0.12),
    });
  }
  return dots;
}

/**
 * The nearest point to `at` that is still inside the outline.
 *
 * Used while dragging. Clamping to the bounding box would let a cluster sit in
 * the notch of an L-shaped bed, which is not in the bed.
 */
export function keepInside(outline: Point[], at: Point): Point {
  if (covers(outline, at)) return at;

  let best: Point | null = null;
  let edge: [Point, Point] | null = null;
  let bestDistance = Infinity;
  for (let i = 0; i < outline.length; i += 1) {
    const a = outline[i]!;
    const b = outline[(i + 1) % outline.length]!;
    const point = nearestOnSegment(a, b, at);
    const distance = (point.x - at.x) ** 2 + (point.y - at.y) ** 2;
    if (distance < bestDistance) {
      bestDistance = distance;
      best = point;
      edge = [a, b];
    }
  }
  if (best === null || edge === null) return at;

  // Inside the line, not on it: a point-in-polygon test answers "outside" for a
  // point on the boundary, so a clamped cluster would fail the very check that
  // clamped it and be clamped again on the next drag.
  //
  // Two centimetres, not one millimetre. A millimetre was the first attempt and
  // it survived every unit test and none of the app: positions are rounded to
  // centimetres before they are stored, so the inset was rounded away and the
  // cluster came back sitting exactly on the corner of the bed. The inset has
  // to be larger than the rounding step it passes through.
  //
  // Along the edge's normal, and both ways — "towards the centroid" is the
  // obvious choice and is wrong for a concave bed. Snapping to the inner edge
  // of an L's lower arm, the centroid lies *across* that edge, so a nudge
  // towards it steps straight back out of the garden.
  const [a, b] = edge;
  const length = Math.hypot(b.x - a.x, b.y - a.y);
  const normals: Array<[number, number]> = [];
  if (length > 0) {
    normals.push([-(b.y - a.y) / length, (b.x - a.x) / length]);
    normals.push([(b.y - a.y) / length, -(b.x - a.x) / length]);
  }
  // The edge's own normal first, then a fan of directions. The nearest point is
  // often a *corner*, and no single edge normal points into the shape there:
  // snapping to the outer corner of an L's arm, both normals run along a
  // boundary and stay on it. Sixteen directions always contain one that is in.
  const STEPS = 16;
  for (let i = 0; i < STEPS; i += 1) {
    const angle = (i / STEPS) * Math.PI * 2;
    normals.push([Math.cos(angle), Math.sin(angle)]);
  }
  for (const [nx, ny] of normals) {
    const tried = { x: best.x + nx * INSET_M, y: best.y + ny * INSET_M };
    if (covers(outline, tried)) return tried;
  }
  return best;
}

function nearestOnSegment(a: Point, b: Point, at: Point): Point {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const length = dx * dx + dy * dy;
  if (length === 0) return a;
  const t = Math.max(0, Math.min(1, ((at.x - a.x) * dx + (at.y - a.y) * dy) / length));
  return { x: a.x + t * dx, y: a.y + t * dy };
}
