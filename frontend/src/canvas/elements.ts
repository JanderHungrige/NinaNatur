import type { GardenOut } from '../api/client';

/**
 * One element of the plan, whichever array the API put it in.
 *
 * The server has had a single `element` table since Wave 11 — being a planting
 * site is a property of the row, not a different kind of thing. The API still
 * answers with `beds` and `obstacles` separately, and the canvas already draws
 * from both. Selection did not: it looked in `obstacles` alone, so labelling a
 * shape "Blumenbeet" moved it across and it silently lost its handles.
 *
 * This is the one place that reunites them.
 */
export interface PlanElement {
  id: number;
  kind: string;
  label: string | null;
  shape: string;
  x: number;
  y: number;
  points: number[][] | null;
  width: number | null;
  constraint_hint: string | null;
  /** The outline in absolute metres. `polygon` on a bed, `footprint` on an
   *  obstacle — the same number under two names. */
  footprint: number[][];
  isBed: boolean;
}

export function elementsOf(garden: GardenOut): PlanElement[] {
  return [
    ...garden.obstacles.map((o) => ({
      id: o.obstacle_id,
      kind: o.kind,
      label: o.label,
      shape: o.shape,
      x: o.x,
      y: o.y,
      points: o.points,
      width: o.width,
      constraint_hint: o.constraint_hint,
      footprint: o.footprint,
      isBed: false,
    })),
    ...garden.beds.map((b) => ({
      id: b.bed_id,
      kind: b.kind,
      label: b.label,
      shape: b.shape,
      x: b.x,
      y: b.y,
      points: b.points,
      width: b.width,
      constraint_hint: b.constraint_hint,
      footprint: b.polygon,
      isBed: true,
    })),
  ];
}

export function elementById(garden: GardenOut, id: number | null): PlanElement | null {
  if (id === null) return null;
  return elementsOf(garden).find((element) => element.id === id) ?? null;
}
