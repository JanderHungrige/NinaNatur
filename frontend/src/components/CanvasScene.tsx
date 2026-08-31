import { bloomDots } from '../canvas/blooms';
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
  /** Grabbing a shape's body: a move, not a pan. */
  onGrabElement?: ((id: number, event: React.PointerEvent) => void) | undefined;
  /** Where the element being dragged is shown while the pointer holds it. */
  dragOffset?: { id: number; dx: number; dy: number } | null;
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

/** Shoelace, on the outline the server already computed. */
function coverage(item: Drawn): number {
  const points = 'bed_id' in item ? item.polygon : item.footprint;
  let sum = 0;
  for (let i = 0; i < points.length; i += 1) {
    const a = points[i]!;
    const b = points[(i + 1) % points.length]!;
    sum += a[0]! * b[1]! - b[0]! * a[1]!;
  }
  return Math.abs(sum) / 2;
}

/**
 * Surfaces behind the things standing on them, and among surfaces the big ones
 * behind the small.
 *
 * Ranking on kind alone was not enough: a bed and a lawn are both surfaces, so
 * they tied, and a stable sort put the beds last — in front. The garden-wide
 * outline then covered every path and every patch of gravel drawn inside it.
 *
 * Size is the rule a plan follows anyway. The whole-garden bed is the largest
 * thing there is, so it falls to the back on its own, and a small bed drawn on
 * a lawn stays visible without anybody special-casing either.
 */
function surfacesFirst(items: Drawn[]): Drawn[] {
  const standing = (item: Drawn): number => {
    const kind = 'bed_id' in item ? PLANTING_KIND : item.kind;
    return BY_KIND.get(kind)?.standing === false ? 0 : 1;
  };
  return [...items].sort(
    (a, b) => standing(a) - standing(b) || coverage(b) - coverage(a),
  );
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
  // A pond has no height, and the server stopped inventing 0.0 for one. The
  // label went on reading it out anyway: "Teich, null m hoch".
  const what = o.height === null ? kind : `${kind}, ${o.height} m hoch`;
  // The free label first when there is one: it is what the user calls the thing.
  return o.label ? `${o.label} (${what})` : what;
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
 * black. An unrecorded colour keeps the hatch and never becomes a fill: colour
 * is recorded for 6.6% of the catalogue, and green, grey or beige all read as
 * an answer the data does not support.
 *
 * Known colours are no longer a fill at all. They were bands across the bed,
 * which says it is half yellow and half blue; what is true is that some of the
 * flowers are yellow. Those are drawn as dots on top instead.
 */
function bloomFill(
  entry: { colours: string[]; unknown: number } | undefined,
): string | null {
  if (entry === undefined) return null;
  return entry.colours.length === 0 && entry.unknown > 0
    ? 'url(#bloom-unknown)'
    : null;
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
  onGrabElement,
  dragOffset = null,
}: Props) {
  /** Shown where the pointer has it, saved where it is let go. */
  const shift = (id: number): string =>
    dragOffset !== null && dragOffset.id === id
      ? `translate(${dragOffset.dx} ${-dragOffset.dy})`
      : '';

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
              transform={shift(item.bed_id)}
              onPointerDown={
                onGrabElement === undefined || armed
                  ? undefined
                  : (event) => onGrabElement(item.bed_id, event)
              }
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
              transform={shift(item.obstacle_id)}
              onPointerDown={
                onGrabElement === undefined || armed
                  ? undefined
                  : (event) => onGrabElement(item.obstacle_id, event)
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

        {/* Flowers, on top of the beds and outside the wobble filter: a dot
            the size of a blossom disappears under a displacement map meant for
            outlines. */}
        <g className="blooms" aria-hidden="true" pointerEvents="none">
          {garden.beds.flatMap((bed) =>
            bloomDots(bed.bed_id, bed.polygon, palette?.[bed.bed_id]?.colours ?? []).map(
              (dot, i) => (
                <circle
                  key={`${bed.bed_id}-${i}`}
                  className="bloom-dot"
                  cx={dot.x}
                  cy={-dot.y}
                  r={dot.r}
                  fill={SWATCH[dot.colour] ?? 'var(--ink-muted)'}
                />
              ),
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
