import type React from 'react';
import { Fragment, type ReactNode } from 'react';

import type { GardenOut } from '../api/client';
import { acrossPairs } from '../canvas/across';
import { svgPoints } from '../canvas/viewport';
import { KINDS, PLANTING_KIND, isGround, labelOf } from '../kinds';
import { bedName } from '../plural';
import type { PlanTheme } from '../themes';

/*
 * The shapes on the plan — every bed and every element, in one ordered group
 * (doc 96). Moved out of CanvasScene when the plan's look became a theme: this
 * is where the theme's fills and its one filter are applied, and nowhere else.
 */

type Bed = GardenOut['beds'][number];
type Obstacle = GardenOut['obstacles'][number];
/** A bed seen as what it is: an element of kind `bed`. */
type Drawn = Obstacle | Bed;

const BY_KIND = new Map(KINDS.map((k) => [k.kind, k]));

/** What a kind is drawn as. Unknown kinds get the plain wash rather than no
 *  fill: an object the server knows and we do not must still be visible. */
function symbolOf(kind: string): string {
  return BY_KIND.get(kind)?.symbol ?? 'plain';
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
export function surfacesFirst(items: Drawn[]): Drawn[] {
  const standing = (item: Drawn): number => {
    const kind = 'bed_id' in item ? PLANTING_KIND : item.kind;
    return BY_KIND.get(kind)?.standing === false ? 0 : 1;
  };
  return [...items].sort(
    (a, b) => standing(a) - standing(b) || coverage(b) - coverage(a),
  );
}

function bedLabel(bed: Bed): string {
  const light =
    bed.sun_hours === null
      ? 'Licht noch nicht berechnet'
      : `${bed.sun_hours.toFixed(1)} Sonnenstunden pro Tag`;
  return `${bedName(bed.name)}, ${light}`;
}

function obstacleLabel(o: Obstacle): string {
  const kind = labelOf(o.kind);
  // A pond has no height, and the server stopped inventing 0.0 for one. The
  // label went on reading it out anyway: "Teich, null m hoch".
  const what = o.height === null ? kind : `${kind}, ${o.height} m hoch`;
  // The free label first when there is one: it is what the user calls the thing.
  return o.label ? `${o.label} (${what})` : what;
}

/** Shift+F10 and the context-menu key are what a keyboard uses for a
 *  right-click, so the menu is not pointer-only. */
function asksWhatItIs(event: React.KeyboardEvent): boolean {
  return event.key === 'ContextMenu' || (event.shiftKey && event.key === 'F10');
}

export interface PlanObjectsProps {
  garden: GardenOut;
  theme: PlanTheme;
  /** The scale the plan is drawn at. Each shape asks the theme what detail its
   *  own size can carry (doc 99); a level worked out once above would give a
   *  shrub the same as a house. */
  metresPerPixel: number;
  selectedBedId: number | null;
  selectedObstacleId: number | null;
  armed: boolean;
  onSelectBed: (bedId: number) => void;
  onSelectObstacle?: ((obstacleId: number) => void) | undefined;
  onAskWhatItIs?: ((id: number, at: { x: number; y: number }) => void) | undefined;
  onGrabElement?: ((id: number, event: React.PointerEvent) => void) | undefined;
  /** Shown where the pointer has it, saved where it is let go. */
  shift: (id: number) => string;
  /** What a theme draws right beneath a shape — its shadow — by the shape's key. */
  beneath?: ReadonlyMap<string, ReactNode> | undefined;
}

type ShapeProps<T> = Omit<PlanObjectsProps, 'garden' | 'beneath'> & { item: T };

function BedShape({ item, theme, metresPerPixel, selectedBedId, armed, onSelectBed,
  onAskWhatItIs, onGrabElement, shift }: ShapeProps<Bed>) {
  return (
    <polygon
      // The menu anchors to this: it has to follow the shape when the page
      // scrolls, and a click coordinate cannot.
      data-element-id={item.bed_id}
      className={item.bed_id === selectedBedId ? 'bed bed--selected' : 'bed'}
      fill={theme.bedFill(theme.lodAt(metresPerPixel, acrossPairs(item.polygon)))}
      points={svgPoints(item.polygon.map((p) => ({ x: p[0] ?? 0, y: p[1] ?? 0 })))}
      tabIndex={armed ? undefined : 0}
      role={armed ? undefined : 'button'}
      aria-pressed={armed ? undefined : item.bed_id === selectedBedId}
      aria-label={bedLabel(item)}
      transform={shift(item.bed_id)}
      onPointerDown={
        onGrabElement === undefined || armed ? undefined : (event) => onGrabElement(item.bed_id, event)
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
        if (asksWhatItIs(event)) {
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
  );
}

function ObstacleShape({ item, theme, metresPerPixel, selectedObstacleId, armed, onSelectObstacle,
  onAskWhatItIs, onGrabElement, shift }: ShapeProps<Obstacle>) {
  // The ground is drawn and nothing else. It is where the plan is measured
  // from and what the server sums over; for the gardener it is the paper, not
  // a thing on it. Every handler below is left off rather than covered over,
  // and the CSS takes it out of hit-testing entirely, so a click inside the
  // garden reaches whatever is actually there — or the empty canvas.
  const ground = isGround(item.kind);
  const choosable = onSelectObstacle !== undefined && !armed && !ground;
  return (
    <polygon
      data-element-id={item.obstacle_id}
      className={`obstacle obstacle--${item.kind}`}
      fill={theme.fill(symbolOf(item.kind),
                       theme.lodAt(metresPerPixel, acrossPairs(item.footprint)), item.kind)}
      /* The footprint the server computed. Re-deriving it here would be a
         third answer to "what ground does this cover", and the two that
         already existed agreed only by accident. */
      points={item.footprint.map((p) => `${p[0] ?? 0},${-(p[1] ?? 0)}`).join(' ')}
      tabIndex={choosable ? 0 : undefined}
      role={choosable ? 'button' : undefined}
      aria-pressed={choosable ? item.obstacle_id === selectedObstacleId : undefined}
      aria-label={obstacleLabel(item)}
      aria-hidden={ground ? true : undefined}
      onClick={choosable ? () => onSelectObstacle?.(item.obstacle_id) : undefined}
      transform={shift(item.obstacle_id)}
      onPointerDown={
        onGrabElement === undefined || armed || ground
          ? undefined
          : (event) => onGrabElement(item.obstacle_id, event)
      }
      onContextMenu={
        onAskWhatItIs === undefined || armed || ground
          ? undefined
          : (event) => {
              event.preventDefault();
              onAskWhatItIs(item.obstacle_id, { x: event.clientX, y: event.clientY });
            }
      }
      onKeyDown={(event) => {
        if (!choosable) return;
        if (asksWhatItIs(event)) {
          event.preventDefault();
          const box = event.currentTarget.getBoundingClientRect();
          onAskWhatItIs?.(item.obstacle_id, { x: box.left, y: box.top });
          return;
        }
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onSelectObstacle?.(item.obstacle_id);
        }
      }}
    >
      <title>{obstacleLabel(item)}</title>
    </polygon>
  );
}

/**
 * One group, one filter run, and one order. Beds used to be drawn in a second
 * pass after every object, which put them in front of everything: a shape drawn
 * on top of a bed could not be clicked, because the click landed on the bed.
 * Since Wave 11 a bed *is* an element, so it belongs in the same ordered list.
 */
export function PlanObjects({ garden, beneath, ...shared }: PlanObjectsProps) {
  return (
    <g className="canvas__objects" filter={shared.theme.objectsFilter ?? undefined}>
      {surfacesFirst([...garden.obstacles, ...garden.beds]).map((item) => {
        const key = 'bed_id' in item ? `bed-${item.bed_id}` : `obstacle-${item.obstacle_id}`;
        return (
          <Fragment key={key}>
            {beneath?.get(key)}
            {'bed_id' in item
              ? <BedShape item={item} {...shared} />
              : <ObstacleShape item={item} {...shared} />}
          </Fragment>
        );
      })}
    </g>
  );
}
