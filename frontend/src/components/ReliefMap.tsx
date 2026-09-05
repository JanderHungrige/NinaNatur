import type { Terrain } from '../api/client';

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

export function ReliefMap({ terrain }: Props) {
  const { cell_m: cell, min_x: minX, min_y: minY, cols, relief } = terrain;

  return (
    <g className="relief-map" aria-hidden="true">
      {relief.map((lit, index) => {
        const col = index % cols;
        const row = Math.floor(index / cols);
        // Away from level in either direction: a slope facing the lamp is
        // lighter, one facing away is darker, and level is neither.
        const ink = (0.5 - lit) * 2;
        if (Math.abs(ink) < 0.02) return null;
        return (
          <rect
            key={index}
            x={minX + col * cell}
            /* The canvas draws y downwards while the grid counts rows
               northwards, so a row's top edge in SVG is its *northern* edge in
               the garden. Getting this wrong mirrors the whole relief and puts
               every hillside on the wrong side of the plan. */
            y={-(minY + (row + 1) * cell)}
            width={cell}
            height={cell}
            fill={ink > 0 ? 'var(--relief-dark)' : 'var(--relief-light)'}
            opacity={Math.min(1, Math.abs(ink)) * STRENGTH}
          />
        );
      })}
    </g>
  );
}
