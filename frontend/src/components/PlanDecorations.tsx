import { type ReactNode, useMemo } from 'react';

import type { GardenOut } from '../api/client';
import { acrossPoints } from '../canvas/across';
import type { Point } from '../canvas/viewport';
import { KINDS, isGround } from '../kinds';
import type { DecoratedShape, Decoration, PlanTheme } from '../themes';
import { surfacesFirst } from './PlanObjects';

/*
 * What a theme draws along its shapes rather than inside them (docs 97, 98):
 * each shape's shadow right beneath it, and ink over every shape. Decoration
 * only — never pointed at or read out, so the shapes in PlanObjects stay the
 * only targets.
 */

const SYMBOL = new Map(KINDS.map((k) => [k.kind, k.symbol]));

interface Decorated {
  id: number;
  shape: DecoratedShape;
  decoration: Decoration;
}

const toPoints = (ring: number[][]) => ring.map((p) => ({ x: p[0] ?? 0, y: p[1] ?? 0 }));

type Bed = GardenOut['beds'][number];
type Obstacle = GardenOut['obstacles'][number];

function bedShape(bed: Bed): DecoratedShape {
  return { key: `bed-${bed.bed_id}`, symbol: 'planting', ground: false, kind: 'bed',
           points: toPoints(bed.polygon), line: null, raised: bed.height_above_ground,
           // A bed lies on the ground: what it shows is its own side, not a cast.
           roofLines: [], roof: 'unknown', shadow: null };
}

function obstacleShape(o: Obstacle): DecoratedShape {
  // A line's points are its centreline, relative to where the element stands.
  const line = o.shape === 'line' && o.points !== null
    ? o.points.map((p) => ({ x: o.x + (p[0] ?? 0), y: o.y + (p[1] ?? 0) }))
    : null;
  return { key: `obstacle-${o.obstacle_id}`, symbol: SYMBOL.get(o.kind) ?? 'plain',
           ground: isGround(o.kind), kind: o.kind, points: toPoints(o.footprint), line,
           raised: 0, roof: o.roof,
           shadow: o.shadow === null || o.shadow === undefined
             ? null : { x: o.shadow[0] ?? 0, y: o.shadow[1] ?? 0 },
           roofLines: o.roof_lines.map((l) => [toPoints(l)[0]!, toPoints(l)[1]!] as [Point, Point]) };
}

/**
 * Every shape's decoration, in the order the shapes are drawn — worked out
 * once per garden and scale, not on every drag frame. The scale moves in
 * halvings rather than with every zoom step: a wobble only needs redrawing
 * when it would change by a pixel.
 */
export const planScale = (metresPerPixel: number): number =>
  2 ** Math.round(Math.log2(metresPerPixel));

export function useDecorations(garden: GardenOut, theme: PlanTheme,
  metresPerPixel: number): Decorated[] | null {
  const scale = planScale(metresPerPixel);
  return useMemo(() => {
    const decorate = theme.decorate;
    if (decorate === undefined) return null;
    return surfacesFirst([...garden.obstacles, ...garden.beds]).map((item) => {
      const shape = 'bed_id' in item ? bedShape(item) : obstacleShape(item);
      const id = 'bed_id' in item ? item.bed_id : item.obstacle_id;
      const lod = theme.lodAt(scale, acrossPoints(shape.points));
      return { id, shape, decoration: decorate(shape, lod, scale) };
    });
  }, [garden, theme, scale]);
}

const isEmpty = (node: ReactNode): boolean =>
  node === null || node === undefined || (Array.isArray(node) && node.length === 0);

/**
 * Each shape's shadow, to be drawn right beneath the shape (doc 98). One layer
 * under every shape put a tree's shadow under the lawn it stands on, and a
 * raised bed's under the path beside it: his shadow is each symbol's own
 * bottom layer, and here it is again.
 */
export function beneathOf(drawn: Decorated[], shift: (id: number) => string,
): ReadonlyMap<string, ReactNode> {
  const beneath = new Map<string, ReactNode>();
  for (const { id, shape, decoration } of drawn) {
    if (isEmpty(decoration.under)) continue;
    // A group only for the shape being dragged, to move its shadow with it.
    const moved = shift(id);
    beneath.set(shape.key, moved === '' ? decoration.under : (
      <g key={`${shape.key}-shadow`} pointerEvents="none" aria-hidden="true" transform={moved}>
        {decoration.under}
      </g>
    ));
  }
  return beneath;
}

/**
 * The ink over every shape. A shape's marks sit in it directly, and only the
 * shape being dragged gets a group, to move them with it: a group per shape
 * was a third of everything the browser had to build for the city.
 */
export function InkLayer({ drawn, theme, metresPerPixel, shift }: {
  drawn: Decorated[];
  theme: PlanTheme;
  metresPerPixel: number;
  shift: (id: number) => string;
}) {
  // Stable while the garden and the scale are: what the theme draws for the
  // plan as a whole is not worked out again on every drag frame.
  const shapes = useMemo(() => drawn.map((d) => d.shape), [drawn]);
  return (
    <g className="canvas__ink" pointerEvents="none" aria-hidden="true">
      {/* What belongs to no single shape — a street network's outline — under
          the shapes' own marks. */}
      {theme.Plan !== undefined && <theme.Plan shapes={shapes} metresPerPixel={metresPerPixel} />}
      {drawn.filter(({ decoration }) => !isEmpty(decoration.over)).map(({ id, shape, decoration }) => {
        const moved = shift(id);
        if (moved === '') return decoration.over;
        return <g key={shape.key} transform={moved}>{decoration.over}</g>;
      })}
    </g>
  );
}
