import { KINDS, PLANTING_KIND, labelOf } from '../kinds';
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
  /** A drawing tool is armed: the plan takes the click, not what is under it.
   *  Without this the first click to draw selects the garden-wide bed and the
   *  page scrolls away to the suggestions, so the tool looks like it needs two
   *  attempts.
   *
   *  The handlers are left off entirely rather than covered with
   *  `pointer-events: none`: not attaching is a guarantee, and a CSS property
   *  is a hope that nothing else ever sets it back. */
  armed?: boolean;
  /** Right-click, or the keyboard's context-menu key, on an element. */
  onAskWhatItIs?:
    | ((id: number, at: { x: number; y: number }) => void)
    | undefined;
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
type Drawn = GardenOut['obstacles'][number] | GardenOut['beds'][number];

/** A bed seen as what it is: an element of kind `bed`. */
function asElement(bed: GardenOut['beds'][number]): Drawn {
  return bed;
}

function surfacesFirst(items: Drawn[]): Drawn[] {
  const rank = (item: Drawn): number => {
    const kind = 'bed_id' in item ? PLANTING_KIND : item.kind;
    return BY_KIND.get(kind)?.standing === false ? 0 : 1;
  };
  return [...items].sort((a, b) => rank(a) - rank(b));
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
  armed = false,
  onAskWhatItIs,
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

        {/* One group, one filter run, and one order. Beds used to be drawn in
            a second pass after every object, which put them in front of
            everything: a shape drawn on top of a bed could not be clicked,
            because the click landed on the bed. Since Wave 11 a bed *is* an
            element, so it belongs in the same ordered list. */}
        <g className="canvas__objects">
        {surfacesFirst([...garden.obstacles, ...garden.beds.map(asElement)]).map((item) =>
          'bed_id' in item ? (
            <polygon
              key={`bed-${item.bed_id}`}
              className={item.bed_id === selectedBedId ? 'bed bed--selected' : 'bed'}
              style={(() => {
                const fill = bloomFill(palette?.[item.bed_id]);
                return fill === null ? undefined : { fill };
              })()}
              points={d(item.polygon.map((p) => ({ x: p[0] ?? 0, y: p[1] ?? 0 })))}
              tabIndex={armed ? undefined : 0}
              role={armed ? undefined : 'button'}
              aria-pressed={armed ? undefined : item.bed_id === selectedBedId}
              aria-label={bedLabel(item)}
              onContextMenu={
                onAskWhatItIs === undefined || armed
                  ? undefined
                  : (event) => {
                      event.preventDefault();
                      onAskWhatItIs(item.bed_id, { x: event.clientX, y: event.clientY });
                    }
              }
              onClick={armed ? undefined : () => onSelectBed(item.bed_id)}
              onKeyDown={(event) => {
                if (armed) return;
                // Shift+F10 and the context-menu key are what a keyboard uses
                // for a right-click, so the menu is not pointer-only.
                if (event.key === 'ContextMenu' || (event.shiftKey && event.key === 'F10')) {
                  event.preventDefault();
                  const box = event.currentTarget.getBoundingClientRect();
                  onAskWhatItIs?.(item.bed_id, { x: box.left, y: box.top });
                  return;
                }
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  onSelectBed(item.bed_id);
                }
              }}
            >
              <title>{bedLabel(item)}</title>
            </polygon>
          ) : (
            <polygon
              key={`obstacle-${item.obstacle_id}`}
              className={`obstacle obstacle--${item.kind}`}
              fill={`url(#symbol-${symbolOf(item.kind)})`}
              /* The footprint the server computed. Re-deriving it here would be
                 a third answer to "what ground does this cover", and the two
                 that already existed agreed only by accident. */
              points={item.footprint.map((p) => `${p[0] ?? 0},${-(p[1] ?? 0)}`).join(' ')}
              tabIndex={onSelectObstacle === undefined || armed ? undefined : 0}
              role={onSelectObstacle === undefined || armed ? undefined : 'button'}
              aria-label={obstacleLabel(item)}
              onClick={
                onSelectObstacle === undefined || armed
                  ? undefined
                  : () => onSelectObstacle(item.obstacle_id)
              }
              onContextMenu={
                onAskWhatItIs === undefined || armed
                  ? undefined
                  : (event) => {
                      event.preventDefault();
                      onAskWhatItIs(item.obstacle_id, { x: event.clientX, y: event.clientY });
                    }
              }
              onKeyDown={(event) => {
                if (onSelectObstacle === undefined || armed) return;
                if (event.key === 'ContextMenu' || (event.shiftKey && event.key === 'F10')) {
                  event.preventDefault();
                  const box = event.currentTarget.getBoundingClientRect();
                  onAskWhatItIs?.(item.obstacle_id, { x: box.left, y: box.top });
                  return;
                }
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  onSelectObstacle(item.obstacle_id);
                }
              }}
            >
              <title>{obstacleLabel(item)}</title>
            </polygon>
          ),
        )}
        </g>

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
