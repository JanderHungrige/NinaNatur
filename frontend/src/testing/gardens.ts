import type {
  BedSuggestions,
  GardenOut,
  ImprovementsOut,
  LightMap,
  ScoreOut,
  TimelineOut,
} from '../api/client';

type Bed = GardenOut['beds'][number];
type Obstacle = GardenOut['obstacles'][number];
type Planting = Bed['plantings'][number];

/*
 * Gardens for tests, in the shapes the API answers with (docs 87, 88).
 *
 * Shared by the App flow tests and the selection's own, so a field the server
 * adds is added in one place. Pure data: nothing here renders or reaches the
 * network.
 */

/** Südbeet: three metres by two, its light measured, nothing planted. */
export function bed(overrides: Partial<Bed> = {}): Bed {
  return {
    bed_id: 1, kind: 'bed', shape: 'polygon', x: 0, y: 0, points: null, width: null,
    constraint_hint: null, name: 'Südbeet', polygon: [[0, 0], [3, 0], [3, 2], [0, 2]],
    soil_type: 'loam', moisture: 'fresh', ellenberg_l: 8, ellenberg_m: 5, ellenberg_n: 5.5,
    ellenberg_r: 6.5, sun_hours: 6.4, slope_deg: null, aspect_deg: null,
    light_computed_at: '2026-08-28T10:00:00+00:00', height_above_ground: 0, label: null,
    plantings: [],
    ...overrides,
  };
}

/** One meadow sage, not placed by hand. */
export function planting(overrides: Partial<Planting> = {}): Planting {
  return {
    planting_id: 11, taxon_id: 3, canonical_name: 'Salvia pratensis', raw_name: null,
    quantity: 1, x: null, y: null, added_at: '2026-09-01T10:00:00+00:00',
    ...overrides,
  };
}

/** A two-by-two shed the gardener called Gartenhaus, beside the bed. */
export function shed(overrides: Partial<Obstacle> = {}): Obstacle {
  return {
    obstacle_id: 5, kind: 'shed', label: 'Gartenhaus', shape: 'polygon', x: 6, y: 0,
    points: [[-1, -1], [1, -1], [1, 1], [-1, 1]], width: null, constraint_hint: null,
    height: 2.4, height_source: 'user', roof: 'unknown', roof_source: 'user', eaves_m: null,
    eaves_source: null, roof_fall_deg: null, roof_pitch_deg: null, roof_lines: [],
    footprint: [[5, -1], [7, -1], [7, 1], [5, 1]],
    ...overrides,
  };
}

export function garden(token: string, name: string, overrides: Partial<GardenOut> = {}): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {},
    share_token: token, name, latitude: 51.2564, longitude: 7.1501, created_at: '',
    updated_at: '', beds: [bed()], obstacles: [],
    ...overrides,
  };
}

/** Something of every kind to select: a bed with a patch in it, and a shed beside it. */
export function richGarden(overrides: Partial<GardenOut> = {}): GardenOut {
  return garden('tok', 'Testgarten', {
    beds: [bed({ plantings: [planting()] })],
    obstacles: [shed()],
    ...overrides,
  });
}

export const timeline = (): TimelineOut => ({
  mode: 'forage',
  months: Array.from({ length: 12 }, (_, i) => ({ month: i + 1, coverage: 0, species: [] })),
  gaps: [], plantings_total: 0, plantings_without_interaction_data: 0, is_empty: true,
});

export const score = (): ScoreOut => ({
  score: 0, by_month: {}, by_species: [], by_group: { bee: 0, butterfly: 0, hoverfly: 0 },
  plantings_total: 0, plantings_without_interaction_data: 0, is_empty: true,
});

export const improvements = (): ImprovementsOut => ({ current_score: 0, additions: [], swaps: [] });

export const suggestions = (): BedSuggestions => ({
  bed_id: 1, bed_name: 'Südbeet', site_axes: { ellenberg_l: 8 }, total: 1, woody: [],
  woody_total: 0, filters: {}, light_state: 'current',
  items: [{
    taxon_id: 7, canonical_name: 'Sambucus nigra', family: 'Adoxaceae', height_max_m: 6,
    flowering_start_month: 6, flowering_end_month: 7, flower_colour: 'white',
    colour_known: true, bird_partners: null, space_m2: null, fits_bed: true,
    fit: { score: 0.9, axes: {} },
  }],
} as BedSuggestions);

export const lightMap = (): LightMap => ({
  cell_m: 1, min_x: 0, min_y: 0, cols: 2, rows: 2, hours: [1, 1, 7, 7],
  roof: [false, false, false, false], max_hours: 7, computed_at: '2026-09-04T10:00:00+00:00',
  stale: false, morning: [0.5, 0.5, 3.5, 3.5], misplaced: [],
} as LightMap);
