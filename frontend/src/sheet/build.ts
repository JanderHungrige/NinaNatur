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
    eaves_m: null, eaves_source: null, roof_fall_deg: null, roof_pitch_deg: null, label: null,
    ...extra,
  };
}

/** A house with a gable roof, the shape most of the sheet's houses have. */
export function house(id: number, at: [number, number], w: number, d: number): Obstacle {
  return element(id, 'house', at, box(w, d), { height: 9, roof: 'gable', eaves_m: 6 });
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
