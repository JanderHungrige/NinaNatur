import type { LightMap } from '../api/client';

export type MapMode = 'sun' | 'shade';

interface Props {
  map: LightMap;
  mode: MapMode;
}

/**
 * Sun hours across the garden, drawn as a wash over the plan.
 *
 * Two readings of one number, because gardeners ask it both ways. **Sun**
 * paints the dark places: more sun, more transparent, so the plan shows through
 * where it is bright and the shade is what stands out. **Shade** does the
 * reverse for somebody hunting a spot for a fern.
 *
 * The wash is one colour per reading rather than a ramp — the plan already
 * spends its colour on flowers and on what things are, and a heat map in red
 * and blue over the top would be two languages at once.
 *
 * Both inks are theme variables, and the dark theme is not a darker version of
 * the light one. Over paper, shade is painted dark and that reads immediately.
 * Over the dark theme's near-black ground *nothing* reads as darker — a
 * near-black wash measures 1.09 contrast against it — so shade is painted in a
 * cool grey that is lighter than the ground, and the legend is what says the
 * wash means shade. Measured before choosing, because the first version used
 * one ink for both themes and was simply not there in the dark one.
 */
export function SunMap({ map, mode }: Props) {
  // Against the sunniest cell rather than against a fixed twelve hours: a
  // garden that never gets more than four is still a garden with a bright end
  // and a dark one, and that difference is the thing worth seeing.
  const brightest = Math.max(map.max_hours, 0.1);

  return (
    <g
      className={`sun-map sun-map--${mode}`}
      aria-hidden="true"
      pointerEvents="none"
    >
      {map.hours.map((hours, index) => {
        const col = index % map.cols;
        const row = Math.floor(index / map.cols);
        const share = Math.min(1, Math.max(0, hours / brightest));
        // Sun: bright cells vanish. Shade: bright cells are the wash.
        const ink = mode === 'sun' ? 1 - share : share;
        if (ink < 0.02) return null;
        return (
          <rect
            key={index}
            className="sun-map__cell"
            x={map.min_x + col * map.cell_m}
            y={-(map.min_y + (row + 1) * map.cell_m)}
            width={map.cell_m}
            height={map.cell_m}
            opacity={ink * 0.8}
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
