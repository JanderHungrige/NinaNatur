import { type ReactNode, useMemo } from 'react';

import type { GardenOut } from '../api/client';
import { KINDS, isGround } from '../kinds';
import type { DecoratedShape, Decoration, LevelOfDetail, PlanTheme } from '../themes';
import { surfacesFirst } from './PlanObjects';

/*
 * What a theme draws along its shapes rather than inside them (doc 97):
 * shadows under every shape, ink over them. Decoration only — neither layer is
 * pointed at or read out, so the shapes in PlanObjects stay the only targets.
 */

const SYMBOL = new Map(KINDS.map((k) => [k.kind, k.symbol]));

interface Decorated {
  id: number;
  shape: DecoratedShape;
  decoration: Decoration;
}

const toPoints = (ring: number[][]) => ring.map((p) => ({ x: p[0] ?? 0, y: p[1] ?? 0 }));

/**
 * Every shape's decoration, in the order the shapes are drawn — worked out
 * once per garden and scale, not on every drag frame. The scale moves in
 * halvings rather than with every zoom step: a wobble only needs redrawing
 * when it would change by a pixel.
 */
export function useDecorations(garden: GardenOut, theme: PlanTheme, lod: LevelOfDetail,
  metresPerPixel: number): Decorated[] | null {
  const scale = 2 ** Math.round(Math.log2(metresPerPixel));
  return useMemo(() => {
    const decorate = theme.decorate;
    if (decorate === undefined) return null;
    return surfacesFirst([...garden.obstacles, ...garden.beds]).map((item) => {
      const shape: DecoratedShape = 'bed_id' in item
        ? { key: `bed-${item.bed_id}`, symbol: 'planting', ground: false, points: toPoints(item.polygon) }
        : { key: `obstacle-${item.obstacle_id}`, symbol: SYMBOL.get(item.kind) ?? 'plain',
            ground: isGround(item.kind), points: toPoints(item.footprint) };
      const id = 'bed_id' in item ? item.bed_id : item.obstacle_id;
      return { id, shape, decoration: decorate(shape, lod, scale) };
    });
  }, [garden, theme, lod, scale]);
}

const isEmpty = (node: ReactNode): boolean =>
  node === null || node === undefined || (Array.isArray(node) && node.length === 0);

/**
 * One of the two layers. A shape's marks sit in it directly, and only the
 * shape being dragged gets a group, to move them with it: a group per shape
 * was a third of everything the browser had to build for the city.
 */
export function DecorationLayer({ drawn, part, shift }: {
  drawn: Decorated[];
  part: 'under' | 'over';
  shift: (id: number) => string;
}) {
  return (
    <g className={part === 'under' ? 'canvas__shadows' : 'canvas__ink'}
       pointerEvents="none" aria-hidden="true">
      {drawn.filter(({ decoration }) => !isEmpty(decoration[part])).map(({ id, shape, decoration }) => {
        const moved = shift(id);
        return moved === '' ? decoration[part] : <g key={shape.key} transform={moved}>{decoration[part]}</g>;
      })}
    </g>
  );
}
