import type { GardenOut } from '../api/client';
import { beds as bedCount, obstacles as obstacleCount } from '../plural';

interface Props {
  garden: GardenOut;
  selectedBedId: number | null;
  onSelectBed: (bedId: number) => void;
}

const VIEW = { minX: -20, minY: -20, width: 40, height: 40 };
const SCALE = 10; // pixels per metre in the viewBox

/** Convert garden metres (y north) to SVG units (y down). */
function toSvg(x: number, y: number): [number, number] {
  return [x * SCALE, -y * SCALE];
}

function bedLabel(bed: GardenOut['beds'][number]): string {
  const light =
    bed.sun_hours === null
      ? 'Licht noch nicht berechnet'
      : `${bed.sun_hours.toFixed(1)} Sonnenstunden pro Tag`;
  return `Beet ${bed.name}, ${light}`;
}

/**
 * The garden plan as SVG rather than <canvas>: every bed and obstacle is a real
 * DOM node, so it can be focused, named, styled and found by a test. The scene is
 * tens of shapes, not thousands, so the performance case for <canvas> does not
 * apply here.
 */
export function GardenCanvas({ garden, selectedBedId, onSelectBed }: Props) {
  return (
    <svg
      className="canvas"
      viewBox={`${VIEW.minX * SCALE} ${-VIEW.minY * SCALE - VIEW.height * SCALE} ${VIEW.width * SCALE} ${VIEW.height * SCALE}`}
      role="group"
      aria-label={`Gartenplan ${garden.name}, ${bedCount(garden.beds.length)}, ${obstacleCount(garden.obstacles.length)}`}
    >
      <defs>
        <pattern id="grid" width={SCALE} height={SCALE} patternUnits="userSpaceOnUse">
          <path d={`M ${SCALE} 0 L 0 0 0 ${SCALE}`} className="grid-line" />
        </pattern>
      </defs>
      <rect
        x={VIEW.minX * SCALE}
        y={-VIEW.minY * SCALE - VIEW.height * SCALE}
        width={VIEW.width * SCALE}
        height={VIEW.height * SCALE}
        fill="url(#grid)"
      />

      {/* North marker — the whole light calculation hinges on which way is up. */}
      <text className="compass" x={0} y={-VIEW.height * SCALE * 0.5 + 14} textAnchor="middle">
        N ↑
      </text>

      {garden.obstacles.map((obstacle) => {
        const [cx, cy] = toSvg(obstacle.x, obstacle.y);
        return (
          <circle
            key={obstacle.obstacle_id}
            className="obstacle"
            cx={cx}
            cy={cy}
            r={obstacle.radius * SCALE}
          >
            <title>{`${obstacle.kind}, ${obstacle.height} m hoch`}</title>
          </circle>
        );
      })}

      {garden.beds.map((bed) => {
        const points = bed.polygon
          .map((point) => {
            const [px, py] = toSvg(point[0] ?? 0, point[1] ?? 0);
            return `${px},${py}`;
          })
          .join(' ');
        return (
          <polygon
            key={bed.bed_id}
            className={bed.bed_id === selectedBedId ? 'bed bed--selected' : 'bed'}
            points={points}
            tabIndex={0}
            role="button"
            aria-pressed={bed.bed_id === selectedBedId}
            aria-label={bedLabel(bed)}
            onClick={() => onSelectBed(bed.bed_id)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onSelectBed(bed.bed_id);
              }
            }}
          >
            <title>{bedLabel(bed)}</title>
          </polygon>
        );
      })}
    </svg>
  );
}
