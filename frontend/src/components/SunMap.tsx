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

/** Where yellow starts, and where it is fully yellow. The band edges the legend
 *  already names, so the map and the legend are one statement. */
const SUN_FROM = 4.0;
const SUN_FULL = 6.0;
/** Where grey starts on the way down, and where it is fully grey. */
const SHADE_FROM = 2.5;
const SHADE_FULL = 0.0;

/** Never solid: the plan underneath is the thing being annotated. */
const MAX_OPACITY = 0.8;
/** Below this the rect is a node the browser composites for nothing. */
const MIN_INK = 0.02;

/** Which ink a cell gets, and how much of it. Null through the middle band. */
export interface Wash {
  ink: 'sun' | 'shade';
  /** 0–1, before `MAX_OPACITY`. */
  strength: number;
}

/**
 * The wash for one cell's hours, on the absolute scale the legend names.
 *
 * Absolute, not scaled against the garden's own brightest cell. That was the
 * earlier design and it was right for a one-ink wash, which only ever claimed
 * *more than the rest of this garden*. Two inks make a stronger claim — yellow
 * says sunny and grey says shady — and a yellow that meant 3 h in one garden
 * and 9 h in another would be saying something untrue in one of them.
 *
 * Structure inside a dark garden survives it, because the ramps are continuous
 * rather than five steps: a courtyard between 0.5 h and 1.5 h still shows its
 * brighter corner, just in two shades of grey instead of grey against yellow.
 * Which is the honest picture of a courtyard.
 *
 * Halbschatten — 2.5 h to 4 h — takes no ink at all. It is the hinge the two
 * readings turn on, and painting it in either colour would pick a side that the
 * hours do not.
 */
export function washFor(hours: number): Wash | null {
  if (hours >= SUN_FROM) {
    return { ink: 'sun', strength: Math.min(1, (hours - SUN_FROM) / (SUN_FULL - SUN_FROM)) };
  }
  if (hours < SHADE_FROM) {
    return {
      ink: 'shade',
      strength: Math.min(1, (SHADE_FROM - hours) / (SHADE_FROM - SHADE_FULL)),
    };
  }
  return null;
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
        const wash = washFor(hours);
        if (wash === null) return null;
        // The day keeps only the sunny half. A grey wash under a grey shadow
        // hides the one thing on the plan that is supposed to be moving.
        if (mode === 'day' && wash.ink === 'shade') return null;
        if (wash.strength < MIN_INK) return null;
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

/** A representative hour count for the band at `index`: its middle, or two
 *  hours past the edge for the open-ended top one. The legend paints its
 *  swatches by running this through `washFor`, so a swatch cannot drift out of
 *  agreement with the map it is explaining. */
export function bandSample(index: number): number {
  const lower = BANDS[index]![0];
  const upper = index === 0 ? null : BANDS[index - 1]![0];
  return upper === null ? lower + 2 : (lower + upper) / 2;
}

/** What to call this many hours. Mirrors the server's `SUN_HOUR_BANDS`, which
 *  is a documented convention rather than physics. */
export function bandFor(hours: number): string {
  for (const [lower, label] of BANDS) {
    if (hours >= lower) return label;
  }
  return BANDS[BANDS.length - 1]![1];
}
