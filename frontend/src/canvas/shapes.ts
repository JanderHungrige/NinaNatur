/**
 * Turning a drag into a shape.
 *
 * Wave 10 stamped elements at a size somebody else chose. This draws them at
 * the size the hand asked for, which is what every drawing tool does and what
 * the feedback on the palette asked for.
 *
 * Everything here works in garden metres and produces what the element model
 * stores: points for an area, a diameter for a circle.
 */
import type { Point } from './viewport';

export type Tool = 'rect' | 'circle' | 'triangle' | 'polygon' | 'freehand';

/** Below this a drag is a mis-click, not a request for a tiny shape. */
export const MIN_DRAG_M = 0.25;

export interface DrawnShape {
  shape: 'rect' | 'circle' | 'polygon';
  x: number;
  y: number;
  width: number | null;
  depth: number | null;
  points: number[][] | null;
  constraintHint: string | null;
}

/** Centimetres. A drawn outline is not a survey. */
const round = (v: number): number => Math.round(v * 100) / 100;

export function shapeFromDrag(tool: Tool, from: Point, to: Point): DrawnShape | null {
  // Absolute, because nobody drags only down and to the right.
  const width = Math.abs(to.x - from.x);
  const depth = Math.abs(to.y - from.y);
  const cx = (from.x + to.x) / 2;
  const cy = (from.y + to.y) / 2;

  if (tool === 'circle') {
    // One measurement, and it is the smaller side: taking the larger would grow
    // the circle past where the pointer actually went.
    const diameter = Math.min(width, depth);
    if (diameter < MIN_DRAG_M) return null;
    return {
      shape: 'circle', x: round(cx), y: round(cy),
      width: round(diameter), depth: null, points: null, constraintHint: null,
    };
  }

  if (width < MIN_DRAG_M || depth < MIN_DRAG_M) return null;

  if (tool === 'triangle') {
    const halfW = round(width / 2);
    const halfD = round(depth / 2);
    return {
      shape: 'polygon', x: round(cx), y: round(cy), width: null, depth: null,
      // Apex up, base along the bottom — the triangle a gardener draws.
      points: [[0, halfD], [halfW, -halfD], [-halfW, -halfD]],
      constraintHint: null,
    };
  }

  return {
    shape: 'rect', x: round(cx), y: round(cy),
    width: round(width), depth: round(depth), points: null,
    // The corners are meant to stay square. The tool honours it; the geometry
    // is points either way.
    constraintHint: 'rect',
  };
}
