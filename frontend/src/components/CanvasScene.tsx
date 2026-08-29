import type { GardenOut } from '../api/client';
import type { Point, Viewport } from '../canvas/viewport';
import { bedName } from '../plural';

interface Props {
  garden: GardenOut;
  view: Viewport;
  spacing: number;
  selectedBedId: number | null;
  draft: Point[];
  onSelectBed: (bedId: number) => void;
  onSelectObstacle?: ((obstacleId: number) => void) | undefined;
}

function bedLabel(bed: GardenOut['beds'][number]): string {
  const light =
    bed.sun_hours === null
      ? 'Licht noch nicht berechnet'
      : `${bed.sun_hours.toFixed(1)} Sonnenstunden pro Tag`;
  return `${bedName(bed.name)}, ${light}`;
}

const KIND_LABEL: Record<string, string> = {
  tree: 'Baum',
  hedge: 'Hecke',
  shrub: 'Strauch',
  building: 'Gebäude',
  wall: 'Mauer',
  fence: 'Zaun',
  other: 'Objekt',
};

function obstacleLabel(o: GardenOut['obstacles'][number]): string {
  const kind = KIND_LABEL[o.kind] ?? o.kind;
  // The free label first when there is one: it is what the user calls the thing.
  return o.label ? `${o.label} (${kind}, ${o.height} m hoch)` : `${kind}, ${o.height} m hoch`;
}

/** Garden metres to the SVG's own coordinates, which run y-down. */
function d(points: Point[]): string {
  return points.map((p) => `${p.x},${-p.y}`).join(' ');
}

/**
 * Everything inside the plan, as pure output.
 *
 * Split from GardenCanvas so the stateful half stays readable: this file knows
 * how the garden looks, that one knows what the pointer is doing.
 */
export function CanvasScene({
  garden,
  view,
  spacing,
  selectedBedId,
  draft,
  onSelectBed,
  onSelectObstacle,
}: Props) {
  return (
    <>
        <defs>
          <pattern
            id="grid"
            width={spacing}
            height={spacing}
            patternUnits="userSpaceOnUse"
          >
            <path d={`M ${spacing} 0 L 0 0 0 ${spacing}`} className="grid-line" />
          </pattern>
        </defs>
        <rect
          x={view.centreX - view.spanM}
          y={-view.centreY - view.spanM}
          width={view.spanM * 2}
          height={view.spanM * 2}
          fill="url(#grid)"
        />

        {/* North marker — the whole light calculation hinges on which way is up. */}
        <text
          className="compass"
          x={view.centreX}
          y={-view.centreY - view.spanM * 0.35}
          textAnchor="middle"
        >
          N ↑
        </text>

        {garden.obstacles.map((obstacle) => (
          <circle
            key={obstacle.obstacle_id}
            className="obstacle"
            cx={obstacle.x}
            cy={-obstacle.y}
            r={obstacle.radius}
            tabIndex={onSelectObstacle === undefined ? undefined : 0}
            role={onSelectObstacle === undefined ? undefined : 'button'}
            aria-label={obstacleLabel(obstacle)}
            onClick={
              onSelectObstacle === undefined
                ? undefined
                : () => onSelectObstacle(obstacle.obstacle_id)
            }
            onKeyDown={(event) => {
              if (onSelectObstacle === undefined) return;
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onSelectObstacle(obstacle.obstacle_id);
              }
            }}
          >
            <title>{obstacleLabel(obstacle)}</title>
          </circle>
        ))}

        {garden.beds.map((bed) => (
          <polygon
            key={bed.bed_id}
            className={bed.bed_id === selectedBedId ? 'bed bed--selected' : 'bed'}
            points={d(bed.polygon.map((p) => ({ x: p[0] ?? 0, y: p[1] ?? 0 })))}
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
        ))}

        {draft.length > 0 && (
          <g data-testid="draft" className="draft">
            <polyline points={d(draft)} className="draft__line" />
            {draft.map((p) => (
              <circle key={`${p.x},${p.y}`} cx={p.x} cy={-p.y} r={spacing * 0.12} />
            ))}
          </g>
        )}
    </>
  );
}
