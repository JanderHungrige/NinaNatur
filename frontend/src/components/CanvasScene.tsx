import { KINDS, labelOf } from '../kinds';
import type { GardenOut } from '../api/client';
import type { Point, Viewport } from '../canvas/viewport';
import { bedName } from '../plural';
import { GardenSymbols } from './GardenSymbols';

interface Props {
  garden: GardenOut;
  view: Viewport;
  spacing: number;
  selectedBedId: number | null;
  draft: Point[];
  viewpoint?: { x: number; y: number } | null;
  onSelectBed: (bedId: number) => void;
  onSelectObstacle?: ((obstacleId: number) => void) | undefined;
  /** Colours in flower per bed for the month being shown, if any. */
  palette?: Record<number, { colours: string[]; unknown: number }> | undefined;
}

const BY_KIND = new Map(KINDS.map((k) => [k.kind, k]));

/** What a kind is drawn as. Unknown kinds get the plain wash rather than no
 *  fill: an object the server knows and we do not must still be visible. */
function symbolOf(kind: string): string {
  return BY_KIND.get(kind)?.symbol ?? 'plain';
}

/**
 * Surfaces first.
 *
 * A lawn belongs under the shed standing on it, and which is which is a
 * property of the kind — not of the order somebody happened to click. Sorted
 * rather than split into two lists so the array keeps one key space.
 */
function surfacesFirst(
  obstacles: GardenOut['obstacles'],
): GardenOut['obstacles'] {
  const rank = (kind: string): number => (BY_KIND.get(kind)?.standing === false ? 0 : 1);
  return [...obstacles].sort((a, b) => rank(a.kind) - rank(b.kind));
}

function bedLabel(bed: GardenOut['beds'][number]): string {
  const light =
    bed.sun_hours === null
      ? 'Licht noch nicht berechnet'
      : `${bed.sun_hours.toFixed(1)} Sonnenstunden pro Tag`;
  return `${bedName(bed.name)}, ${light}`;
}


function obstacleLabel(o: GardenOut['obstacles'][number]): string {
  const kind = labelOf(o.kind);
  // The free label first when there is one: it is what the user calls the thing.
  return o.label ? `${o.label} (${kind}, ${o.height} m hoch)` : `${kind}, ${o.height} m hoch`;
}

// Patterns are sized relative to the bed rather than in metres. Metres were the
// first attempt and the wrong unit twice over: a six-metre band is wider than
// most beds, and even sub-metre bands tile from the SVG origin rather than from
// the shape. `objectBoundingBox` says what is actually meant — split this bed
// into one band per colour, whatever size the bed is.

const SWATCH: Record<string, string> = {
  yellow: '#e8c33a',
  white: '#f4f2ea',
  pink: '#e59ab8',
  violet: '#8f6fc4',
  blue: '#5b8ed6',
  red: '#cf5b4e',
  green: '#6a9a4e',
  orange: '#e08a3c',
  brown: '#9a7b52',
  black: '#3a3a3a',
};

/**
 * The fill for a bed in the month being shown.
 *
 * `null` means "render as usual" — a bed with nothing in flower is empty, not
 * black. An unrecorded colour gets the hatch and never a fill: colour is
 * recorded for 6.6% of the catalogue, and green, grey or beige all read as an
 * answer the data does not support.
 */
function bloomFill(
  entry: { colours: string[]; unknown: number } | undefined,
): string | null {
  if (entry === undefined) return null;
  if (entry.colours.length > 0) return `url(#bloom-${entry.colours.join('-')})`;
  return entry.unknown > 0 ? 'url(#bloom-unknown)' : null;
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
  viewpoint = null,
  onSelectBed,
  onSelectObstacle,
  palette,
}: Props) {
  const combinations = Object.values(palette ?? {})
    .map((e) => e.colours)
    .filter((c) => c.length > 0);

  return (
    <>
        <defs>
        <GardenSymbols />
        {/* "We never recorded it" is its own mark, not a colour. A fill here
            would be the most confident thing this UI draws, about the trait it
            knows least. */}
        <pattern
          id="bloom-unknown"
          width="0.14"
          height="0.14"
          patternUnits="objectBoundingBox"
          patternContentUnits="objectBoundingBox"
        >
          <rect width="0.14" height="0.14" className="bloom-hatch__ground" />
          <rect width="0.07" height="0.14" className="bloom-hatch__line" />
        </pattern>
        {combinations.map((combo) => (
          <pattern
            key={combo.join('-')}
            id={`bloom-${combo.join('-')}`}
            width="1"
            height="1"
            patternUnits="objectBoundingBox"
            patternContentUnits="objectBoundingBox"
          >
            {/* Bands, never a blend: mixing yellow and blue into green would
                invent a flower nobody planted. */}
            {combo.map((colour, i) => (
              <rect
                key={colour}
                x={i / combo.length}
                width={1 / combo.length}
                height="1"
                fill={SWATCH[colour] ?? 'var(--ink-muted)'}
              />
            ))}
          </pattern>
        ))}
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

        {/* One group, one filter run. The wobble is what makes the plan look
            drawn rather than plotted. */}
        <g className="canvas__objects">
        {surfacesFirst(garden.obstacles).map((obstacle) => (
          <polygon
            key={obstacle.obstacle_id}
            className={`obstacle obstacle--${obstacle.kind}`}
            fill={`url(#symbol-${symbolOf(obstacle.kind)})`}
            /* The footprint the server computed. Re-deriving it here would be a
               third answer to "what ground does this cover", and the two that
               already existed agreed only by accident. */
            points={obstacle.footprint.map((p) => `${p[0] ?? 0},${-(p[1] ?? 0)}`).join(' ')}
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
          </polygon>
        ))}
        </g>

        {garden.beds.map((bed) => (
          <polygon
            key={bed.bed_id}
            className={bed.bed_id === selectedBedId ? 'bed bed--selected' : 'bed'}
            style={(() => {
              const fill = bloomFill(palette?.[bed.bed_id]);
              return fill === null ? undefined : { fill };
            })()}
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

        {viewpoint !== null && (
        <g className="viewpoint" data-testid="viewpoint">
          <circle cx={viewpoint.x} cy={-viewpoint.y} r={0.35} />
          <title>Standpunkt</title>
        </g>
      )}

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
