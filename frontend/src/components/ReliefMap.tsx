import { memo, useMemo } from 'react';

import type { Terrain } from '../api/client';
import { cellPaths } from '../canvas/cellPaths';

interface Props {
  terrain: Terrain;
}

/**
 * The shape of the ground, under everything else on the plan.
 *
 * A grid of metres tells a reader nothing — 252.8 to 278.6 is a column of
 * numbers. The same grid lit from the north-west is a landscape at a glance,
 * which is why every map in the world does this.
 *
 * **Deliberately faint.** This is the thing the garden sits on, not the thing
 * the garden is: it has to be readable when somebody looks for it and invisible
 * when they are placing a bed. The server sends lit-ness already computed, so
 * this draws opacity and nothing else — one grey, two directions, no ramp of
 * colour competing with the flowers.
 */

/** How dark the darkest slope gets. Higher than this and the plan swims. */
const STRENGTH = 0.22;

/** Steps of slope, each way. A path per step rather than a rect per metre
 *  (#11): eight are finer than a faint grey can show. */
const STEPS = 8;

function ReliefPaths({ terrain }: Props) {
  const paths = useMemo(() => [...cellPaths(terrain, (index) => {
    // Away from level in either direction: a slope facing the lamp is
    // lighter, one facing away is darker, and level is neither.
    const ink = (0.5 - (terrain.relief[index] ?? 0.5)) * 2;
    if (Math.abs(ink) < 0.02) return null;
    const step = Math.max(1, Math.round(Math.min(1, Math.abs(ink)) * STEPS));
    return `${ink > 0 ? 'dark' : 'light'}|${step}`;
  })], [terrain]);

  return (
    <g className="relief-map" aria-hidden="true">
      {paths.map(([key, d]) => {
        const [side, step] = key.split('|');
        return (
          <path key={key} d={d} fill={`var(--relief-${side})`}
                opacity={(Number(step) / STEPS) * STRENGTH} />
        );
      })}
    </g>
  );
}

export const ReliefMap = memo(ReliefPaths);
