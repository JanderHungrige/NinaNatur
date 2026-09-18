import { useCallback, useRef, useState } from 'react';

import type { DrawnShape, Tool } from './shapes';
import { useEscapeKey } from './useEscapeKey';
import { useFreehandStroke } from './useFreehandStroke';
import { usePolygonDraft } from './usePolygonDraft';
import { useShapeBand } from './useShapeBand';
import type { Viewport } from './viewport';

interface Options {
  tool: Tool | null;
  view: Viewport;
  /** One grid square, in metres. */
  spacing: number;
  onDrawBed?: ((polygon: number[][]) => void) | undefined;
  onDrawShape?: ((shape: DrawnShape) => void) | undefined;
  onDrawTrace?: ((trace: { kind: 'area' | 'path'; points: number[][] }) => void) | undefined;
  onCancelTool?: (() => void) | undefined;
  onClearSelection?: (() => void) | undefined;
}

/**
 * The plan's three ways of drawing — a polygon corner by corner, a shape
 * dragged out, a freehand stroke — and the one way out of all of them.
 *
 * Moved out of GardenCanvas when houses, streets and two fingers came in
 * (doc 87, B1), to keep that file under the 300-line rule. Nothing here
 * changed with the move.
 */
export function useDrawingModes({
  tool,
  view,
  spacing,
  onDrawBed,
  onDrawShape,
  onDrawTrace,
  onCancelTool,
  onClearSelection,
}: Options) {
  // Derived, not stored: the polygon tool *is* the drawing mode, and two
  // places holding the same fact is how they end up disagreeing.
  const drawing = tool === 'polygon';
  const [problem, setProblem] = useState<string | null>(null);

  //  Held in refs so `cancel` can stay a stable callback: the Escape handler
  //  depends on it, and re-registering that listener on every render is how a
  //  keypress ends up handled twice.
  const cancelStroke = useRef<() => void>(() => undefined);
  const cancelBand = useRef<() => void>(() => undefined);
  const clearDraft = useRef<() => void>(() => undefined);

  /** Freehand mode, and the stroke being drawn in it.
   *
   * The points live in a ref and are mirrored into state for drawing. The ref
   * is what pointerup reads: state read from a render closure is one render
   * behind whenever events arrive faster than React re-renders, and losing the
   * last points of a stroke that way would be invisible until it wasn't. */
  const freehandStroke = useFreehandStroke({
    view,
    onTrace: (trace) => onDrawTrace?.(trace),
    onProblem: setProblem,
  });
  cancelStroke.current = freehandStroke.cancel;
  const shapeBand = useShapeBand({
    tool,
    onShape: (shape) => onDrawShape?.(shape),
    onProblem: setProblem,
  });
  cancelBand.current = shapeBand.cancel;
  const polygon = usePolygonDraft({
    onShape: (outline) => onDrawBed?.(outline),
    onProblem: setProblem,
    onDone: () => cancel(),
    // A corner within one grid square of the first is a closure. In metres, so
    // it means the same distance however far the user has zoomed.
    closeWithin: spacing,
  });
  clearDraft.current = polygon.clear;

  /** Leave every drawing mode and forget what was half-drawn. Stable, because
   *  the Escape listener depends on it and re-registering that on every render
   *  is how one keypress ends up handled twice. */
  const cancel = useCallback(() => {
    onCancelTool?.();
    cancelBand.current();
    cancelStroke.current();
    onClearSelection?.();
    clearDraft.current();
    setProblem(null);
  }, [onClearSelection]);

  // Always listening: Escape clears a selection too, and a selection can
  // outlive every drawing mode. Typed into a text field it is the field's (doc 88).
  useEscapeKey(cancel);

  return { drawing, problem, freehandStroke, stroke: freehandStroke.stroke, shapeBand, polygon, cancel };
}
