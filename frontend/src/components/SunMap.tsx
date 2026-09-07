import type { LightMap } from '../api/client';

/** What is drawn over the plan. Exactly one of the two at a time.
 *
 * `day` is not a second heat map: it is the sunny half of the same wash — the
 * ground the day's moving obstacle shadows travel over. Painting the shady half
 * as well would put a grey wash under a grey shadow, and the thing that moves
 * has to be the thing that changes colour.
 */
export type MapMode = 'hours' | 'day';

interface Props {
  map: LightMap;
  mode: MapMode;
}

/** Which ink a cell gets, and how much of it. */
export interface Wash {
  ink: 'sun' | 'shade';
  /** 0–1, before `MAX_OPACITY`. */
  strength: number;
}

/** One step of the wash: everything from `from` hours up to the step above it. */
export interface Level {
  /** Lower bound in hours. */
  from: number;
  /** Null through the middle, where the plan itself shows. */
  ink: 'sun' | 'shade' | null;
  strength: number;
  /** The gardening name, where this step is where one begins. */
  name?: string;
}

/**
 * The steps the map is drawn in, brightest first.
 *
 * **Ten of them, and four above "volle Sonne".** The first
 * version ramped from 4 h and reached full yellow at 6, which is where the
 * plant-label convention stops caring. Measured on a real garden, 139 of its
 * 165 answered cells were above 6 h — so the map painted five sixths of the
 * garden in one flat colour and the honest reading was "it is sunny here",
 * which the gardener already knew.
 *
 * A garden's real range at 51°N, averaged March to October, runs to about
 * 12.5 h. These steps spread across that, so the thing the map is for — *which
 * corner is better than which* — is visible again.
 *
 * Steps rather than a continuous ramp: two hundred cells of smoothly varying
 * opacity read as mush, and the same cells in bands read as contours.
 *
 * The names are the same convention `BANDS` carries, and a test asserts they
 * agree. They are attached to the step where each band begins; the steps
 * between are increments of the same wash, not new names.
 */
export const LEVELS: readonly Level[] = [
  { from: 11.0, ink: 'sun', strength: 1.0 },
  { from: 9.0, ink: 'sun', strength: 0.82 },
  { from: 7.5, ink: 'sun', strength: 0.64 },
  { from: 6.0, ink: 'sun', strength: 0.48, name: 'volle Sonne' },
  { from: 5.0, ink: 'sun', strength: 0.32 },
  { from: 4.0, ink: 'sun', strength: 0.18, name: 'sonnig' },
  { from: 2.5, ink: null, strength: 0, name: 'Halbschatten' },
  { from: 1.5, ink: 'shade', strength: 0.26, name: 'Schatten' },
  { from: 0.75, ink: 'shade', strength: 0.54 },
  { from: 0.0, ink: 'shade', strength: 0.82, name: 'tiefer Schatten' },
];

/** Never solid: the plan underneath is the thing being annotated. */
const MAX_OPACITY = 0.8;

/**
 * The wash for one cell's hours, on the absolute scale the legend names.
 *
 * Absolute, not scaled against the garden's own brightest cell. That was the
 * earlier design and it was right for a one-ink wash, which only ever claimed
 * *more than the rest of this garden*. Two inks make a stronger claim — yellow
 * says sunny and grey says shady — and a yellow that meant 3 h in one garden
 * and 9 h in another would be saying something untrue in one of them.
 *
 * Halbschatten — 2.5 h to 4 h — takes no ink at all. It is the hinge the two
 * readings turn on, and painting it in either colour would pick a side that the
 * hours do not.
 */
export function washFor(hours: number): Wash | null {
  for (const level of LEVELS) {
    if (hours >= level.from) {
      return level.ink === null ? null : { ink: level.ink, strength: level.strength };
    }
  }
  return null;
}

/** The hours at a point in garden metres.
 *
 * `undefined` outside the grid, `null` where the grid has no answer — a cell
 * under a house or a shed, which is roof rather than ground. The two are
 * different things to say and the readout says both.
 */
export function hoursAt(map: LightMap, x: number, y: number): number | null | undefined {
  // Not finite is not a point. An SVG that has not been laid out measures zero
  // and the viewport arithmetic hands back NaN — and NaN passes every bounds
  // test below, because every comparison against it is false. It then indexed
  // the array with NaN, got undefined, and the readout said "roof" over an open
  // lawn. Found in a test, and reachable in the app before the first measure.
  if (!Number.isFinite(x) || !Number.isFinite(y)) return undefined;
  const col = Math.floor((x - map.min_x) / map.cell_m);
  const row = Math.floor((y - map.min_y) / map.cell_m);
  if (col < 0 || col >= map.cols || row < 0 || row >= map.rows) return undefined;
  const hours = map.hours[row * map.cols + col];
  // Explicitly: a missing index is not a roof. Only a stored null is.
  return hours === undefined ? undefined : hours;
}

/**
 * Sun hours across the garden, drawn as a wash over the plan.
 *
 * One map in two inks, because it is one number. It used to be two modes — a
 * dark wash on the shade, or a yellow wash on the sun, whichever way round the
 * gardener wanted to ask — and each of them left half the garden blank, so
 * reading the whole picture meant switching back and forth and remembering.
 * Yellow for sun and grey for shade says both at once.
 *
 * The wash is two flat inks rather than a continuous ramp through orange: the
 * plan already spends its colour on flowers and on what things are, and a heat
 * map in red and blue over the top would be two languages at once.
 *
 * Both inks are theme variables, and the dark theme is not a darker version of
 * the light one. Over paper, shade is painted dark and that reads immediately.
 * Over the dark theme's near-black ground *nothing* reads as darker — a
 * near-black wash measures 1.09 contrast against it — so shade is painted in a
 * cool grey that is lighter than the ground. Measured before choosing, because
 * the first version used one ink for both themes and was simply not there in
 * the dark one.
 */
export function SunMap({ map, mode }: Props) {
  return (
    <g
      className={`sun-map sun-map--${mode}`}
      aria-hidden="true"
      pointerEvents="none"
    >
      {map.hours.map((hours, index) => {
        // Null is a cell with no ground under it — a house or a shed. Drawing
        // nothing is the point: the plan already shows the building there, and
        // painting it in the deep-shade ink would be a claim about a roof that
        // is, in fact, in full sun.
        if (hours === null) return null;
        const wash = washFor(hours);
        if (wash === null || wash.strength <= 0) return null;
        // The day keeps only the sunny half. A grey wash under a grey shadow
        // hides the one thing on the plan that is supposed to be moving.
        if (mode === 'day' && wash.ink === 'shade') return null;
        const col = index % map.cols;
        const row = Math.floor(index / map.cols);
        return (
          <rect
            key={index}
            className={`sun-map__cell sun-map__cell--${wash.ink}`}
            x={map.min_x + col * map.cell_m}
            y={-(map.min_y + (row + 1) * map.cell_m)}
            width={map.cell_m}
            height={map.cell_m}
            opacity={wash.strength * MAX_OPACITY}
          />
        );
      })}
    </g>
  );
}

/** The five bands the legend names, brightest first. */
export const BANDS: ReadonlyArray<readonly [number, string]> = [
  [6, 'volle Sonne'],
  [4, 'sonnig'],
  [2.5, 'Halbschatten'],
  [1.5, 'Schatten'],
  [0, 'tiefer Schatten'],
];

/** What to call this many hours. Mirrors the server's `SUN_HOUR_BANDS`, which
 *  is a documented convention rather than physics. */
export function bandFor(hours: number): string {
  for (const [lower, label] of BANDS) {
    if (hours >= lower) return label;
  }
  return BANDS[BANDS.length - 1]![1];
}
