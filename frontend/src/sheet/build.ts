import type { GardenOut } from '../api/client';
import type { ColourLike } from '../canvas/clusters';
import { heightOf } from '../kinds';

/*
 * Builders for the contact sheet's gardens (doc 95): elements in the shape the
 * API sends them, so what the sheet shows is what the app would draw.
 */

type Obstacle = GardenOut['obstacles'][number];
type Bed = GardenOut['beds'][number];
type Planting = Bed['plantings'][number];

/** Corners of a w × d rectangle around its own centre, as the API stores them. */
export function box(w: number, d: number): number[][] {
  return [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]];
}

/** A round outline — a crown, a pond — as twelve corners. */
export function disc(r: number, corners = 12): number[][] {
  return Array.from({ length: corners }, (_, i) => {
    const a = (i / corners) * 2 * Math.PI;
    return [Math.round(r * Math.cos(a) * 100) / 100, Math.round(r * Math.sin(a) * 100) / 100];
  });
}

/**
 * The offset the server sends for a thing of this height (`shadow`, doc 99):
 * where its shadow falls at the drawing's one moment. These are that moment's
 * real numbers for a garden at 51° north — 15 June, three hours after solar
 * noon, when the sun stands 45.7° up in the west-south-west — so the sheet
 * shows what the app shows. Sheet data only: nothing here works out a sun.
 */
const SHADOW_PER_METRE: [number, number] = [0.904, 0.363];

export function castBy(height: number | null): number[] | null {
  if (height === null || height <= 0) return null;
  const round = (v: number) => Math.round(v * 1000) / 1000;
  return [round(height * SHADOW_PER_METRE[0]), round(height * SHADOW_PER_METRE[1])];
}

/** An element standing at `at`, its outline relative to that and absolute beside it. */
export function element(
  id: number,
  kind: string,
  at: [number, number],
  corners: number[][],
  extra: Partial<Obstacle> = {},
): Obstacle {
  const [x, y] = at;
  return {
    obstacle_id: id, kind, x, y, shape: 'polygon', width: null, constraint_hint: null,
    points: corners, footprint: corners.map(([cx, cy]) => [(cx ?? 0) + x, (cy ?? 0) + y]),
    height: heightOf(kind), height_source: 'user', roof: 'unknown', roof_source: 'user',
    shadow: castBy(heightOf(kind)),
    eaves_m: null, eaves_source: null, roof_fall_deg: null, roof_pitch_deg: null, roof_lines: [], label: null,
    ...extra,
  };
}

/**
 * The lines the server's roof model sends for a roof square to the axes
 * (`roof_lines`, doc 98; tests/test_roof_lines.py): a gable's ridge along the
 * long side, a hip's shortened ridge and its four hips, a south-falling pent's
 * upper edge, nothing for a flat roof. Sheet data only — the app takes these
 * from the server and works none of it out.
 */
export function roofLinesOf(at: [number, number], w: number, d: number, roof: string): number[][][] {
  const [x, y] = at;
  const long = Math.max(w, d) / 2;
  const short = Math.min(w, d) / 2;
  const along = (a: number, b = 0): number[] => (w >= d ? [x + a, y + b] : [x + b, y + a]);
  if (roof === 'gable') return [[along(-long), along(long)]];
  if (roof === 'hip') {
    const half = long - short;
    const ends = half > 0 ? [[along(-half), along(half)]] : [];
    return [...ends, ...[-1, 1].flatMap((end) => [-1, 1].map((side) =>
      [along(end * half), along(end * long, side * short)]))];
  }
  if (roof === 'pent') return [[[x - w / 2, y + d / 2], [x + w / 2, y + d / 2]]];
  return [];
}

/** A house with a gable roof, the shape most of the sheet's houses have. */
export function house(id: number, at: [number, number], w: number, d: number,
  roof = 'gable', extra: Partial<Obstacle> = {}): Obstacle {
  return element(id, 'house', at, box(w, d), {
    // A pitched roof shades from between its eaves and its ridge, as the
    // server's `shading_height` has it (doc 32): 6 m of wall, half the gable.
    height: 9, roof, eaves_m: 6, shadow: castBy(7.5),
    roof_lines: roofLinesOf(at, w, d, roof), ...extra,
  });
}

/** An element drawn along a line: its points are the line, its footprint the
 *  band `width` wide around it, as the API sends one. Straight lines only. */
export function lineElement(id: number, kind: string, from: [number, number], to: [number, number],
  width: number): Obstacle {
  const [dx, dy] = [to[0] - from[0], to[1] - from[1]];
  const run = Math.hypot(dx, dy);
  const [nx, ny] = [(-dy / run) * (width / 2), (dx / run) * (width / 2)];
  const band = [[from[0] + nx, from[1] + ny], [to[0] + nx, to[1] + ny],
    [to[0] - nx, to[1] - ny], [from[0] - nx, from[1] - ny]];
  return {
    ...element(id, kind, from, band.map(([bx, by]) => [bx! - from[0], by! - from[1]])),
    shape: 'line', width, points: [[0, 0], [dx, dy]], footprint: band,
  };
}

/** A bed: its outline absolute, as beds are sent. */
export function bed(
  id: number,
  name: string,
  at: [number, number],
  corners: number[][],
  plantings: Planting[] = [],
  extra: Partial<Bed> = {},
): Bed {
  const [x, y] = at;
  return {
    bed_id: id, kind: 'bed', shape: 'polygon', x: 0, y: 0, points: null, width: null,
    constraint_hint: null, name, polygon: corners.map(([cx, cy]) => [(cx ?? 0) + x, (cy ?? 0) + y]),
    soil_type: 'loam', moisture: 'fresh', ellenberg_l: 7, ellenberg_m: 5, ellenberg_n: 5,
    ellenberg_r: 6, sun_hours: 6, slope_deg: null, aspect_deg: null, light_computed_at: null,
    height_above_ground: 0, label: null, plantings,
    ...extra,
  };
}

/** Species the sheet plants, by taxon: a name, a colour and when it flowers. */
export const SPECIES: Record<number, { name: string; colour: string; months: number[] }> = {
  1: { name: 'Salvia pratensis', colour: 'violet', months: [5, 6, 7] },
  2: { name: 'Leucanthemum vulgare', colour: 'white', months: [5, 6, 7, 8] },
  3: { name: 'Lotus corniculatus', colour: 'yellow', months: [6, 7, 8] },
  4: { name: 'Knautia arvensis', colour: 'pink', months: [6, 7, 8] },
  5: { name: 'Centaurea cyanus', colour: 'blue', months: [6, 7] },
  6: { name: 'Papaver rhoeas', colour: 'red', months: [5, 6] },
  7: { name: 'Calendula officinalis', colour: 'orange', months: [6, 7, 8, 9] },
  8: { name: 'Helleborus niger', colour: 'white', months: [1, 2, 3] },
};

/** `quantity` of one species in a bed, placed where the app would place it. */
export function planting(id: number, taxon: number, quantity: number): Planting {
  return {
    planting_id: id, taxon_id: taxon, canonical_name: SPECIES[taxon]?.name ?? null,
    raw_name: null, quantity, x: null, y: null, added_at: '2026-09-18T00:00:00+00:00',
  };
}

/** What colour each planting of a garden flowers in, and when — what the app fetches. */
export function coloursFor(garden: GardenOut): ColourLike[] {
  return garden.beds.flatMap((b) =>
    b.plantings.map((p) => {
      const species = p.taxon_id === null ? undefined : SPECIES[p.taxon_id];
      return {
        planting_id: p.planting_id,
        colour: species?.colour ?? null,
        months: species?.months ?? [],
        space_m2: null,
      };
    }),
  );
}

/** A garden around its elements, dated so nothing in it depends on today. */
export function gardenOf(name: string, beds: Bed[], obstacles: Obstacle[]): GardenOut {
  return {
    unidentified_plantings: 0, share_token: 'kontaktbogen', name,
    latitude: 51.2564, longitude: 7.1501, created_at: '2026-09-18T00:00:00+00:00',
    updated_at: '2026-09-18T00:00:00+00:00', soil_type: 'loam', moisture: 'fresh',
    observed_colours: {}, beds, obstacles,
  };
}
