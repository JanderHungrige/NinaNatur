import { useCallback, useEffect, useRef, useState } from 'react';

import type { GardenOut } from '../api/client';
import { type Box, boxOf } from '../canvas/handles';
import { useHandleDrag } from '../canvas/useHandleDrag';
import { useVertexDrag } from '../canvas/useVertexDrag';
import { usePolygonDraft } from '../canvas/usePolygonDraft';
import { useViewport } from '../canvas/useViewport';
import { useCanvasGestures } from '../canvas/useCanvasGestures';
import { useFreehandStroke } from '../canvas/useFreehandStroke';
import { useShapeBand } from '../canvas/useShapeBand';
import type { DrawnShape, Tool } from '../canvas/shapes';
import { gridSpacing, viewBox } from '../canvas/viewport';
import { beds as bedCount, obstacles as obstacleCount } from '../plural';
import { CanvasControls } from './CanvasControls';
import { CanvasScene } from './CanvasScene';
import { CanvasOverlays } from './CanvasOverlays';

interface Props {
  garden: GardenOut;
  selectedBedId: number | null;
  onSelectBed: (bedId: number) => void;
  /**
   * The drawing surface's pixel size. Passed rather than measured: an SVG that
   * has not been laid out yet reports zero in a real browser as surely as it
   * does in jsdom, and a zero width turns every pointer position into NaN
   * metres.
   */
  /**
   * Overrides the measured size. Tests pass it because jsdom lays nothing out;
   * in the browser the element measures itself, since assuming 800×600 for a
   * surface that is actually 633×292 converts every click to the wrong metre.
   */
  size?: { widthPx: number; heightPx: number } | undefined;
  onDrawBed?: ((polygon: number[][]) => void) | undefined;
  onSelectObstacle?: ((obstacleId: number) => void) | undefined;
  palette?: Record<number, { colours: string[]; unknown: number }> | undefined;
  /** Where the user is standing, if anywhere. */
  viewpoint?: { x: number; y: number } | null;
  /** Placing one: a second thing a click on the plan can mean, so it is a mode. */
  onPlaceViewpoint?: ((x: number, y: number) => void) | undefined;
  /** The shape tool that is armed, if any. A drag then draws instead of panning. */
  tool?: Tool | null;
  onDrawShape?: ((shape: DrawnShape) => void) | undefined;
  /** A freehand stroke: an outline the hand closed, or a path. */
  onDrawTrace?:
    | ((trace: { kind: 'area' | 'path'; points: number[][] }) => void)
    | undefined;
  /** Escape and "Abbrechen" put the tool down; the parent owns which one it is. */
  onCancelTool?: (() => void) | undefined;
  /** Escape also drops whatever is selected — one key out of everything. */
  onClearSelection?: (() => void) | undefined;
  /** The object wearing handles. Selection is the parent's, because the panel
   *  and the plan must agree on what is being edited. */
  selectedObstacleId?: number | null;
  onResizeObstacle?: ((obstacleId: number, box: Box) => void) | undefined;
  /** Editing the outline itself, corner by corner. */
  onReshapeObstacle?: ((obstacleId: number, points: number[][]) => void) | undefined;
}


/**
 * The garden plan, and the surface it is drawn on.
 *
 * SVG rather than <canvas>: every bed and obstacle is a real DOM node, so it can
 * be focused, named and found by a test, and the scene is tens of shapes rather
 * than thousands. The arithmetic lives in ../canvas, where it can be tested
 * without rendering anything.
 */
export function GardenCanvas({
  garden,
  selectedBedId,
  onSelectBed,
  size,
  onDrawBed,
  onSelectObstacle,
  palette,
  viewpoint = null,
  onPlaceViewpoint,
  selectedObstacleId = null,
  onResizeObstacle,
  tool = null,
  onDrawShape,
  onDrawTrace,
  onCancelTool,
  onClearSelection,
  onReshapeObstacle,
}: Props) {
  const { view, setView, surface, zoom } = useViewport(size);
  const [placing, setPlacing] = useState(false);
  const spacing = gridSpacing(view);

  const selected =
    garden.obstacles.find((o) => o.obstacle_id === selectedObstacleId) ?? null;
  // Derived rather than stored: Wave 11 keeps points, and the box the handles
  // work in is read back off them.
  const selectedBox: Box | null = selected === null ? null : boxOf(selected);
  const { preview, grabHandle } = useHandleDrag({
    selectedBox,
    keepSquare: selected?.shape === 'circle',
    view,
    surface,
    onFinish: (box) => {
      if (selected !== null) onResizeObstacle?.(selected.obstacle_id, box);
    },
  });
  const reshape = (points: number[][]) => {
    if (selected !== null) onReshapeObstacle?.(selected.obstacle_id, points);
  };
  const vertexDrag = useVertexDrag({
    points: selected?.points ?? null,
    origin: { x: selected?.x ?? 0, y: selected?.y ?? 0 },
    view,
    surface,
    onFinish: reshape,
  });

  // Derived, not stored: the polygon tool *is* the drawing mode, and two
  // places holding the same fact is how they end up disagreeing.
  const drawing = tool === 'polygon';
  /** Freehand mode, and the stroke being drawn in it.
   *
   * The points live in a ref and are mirrored into state for drawing. The ref
   * is what pointerup reads: state read from a render closure is one render
   * behind whenever events arrive faster than React re-renders, and losing the
   * last points of a stroke that way would be invisible until it wasn't. */
  const [problem, setProblem] = useState<string | null>(null);

  //  Held in refs so `cancel` can stay a stable callback: the Escape handler
  //  depends on it, and re-registering that listener on every render is how a
  //  keypress ends up handled twice.
  const cancelStroke = useRef<() => void>(() => undefined);
  const freehandStroke = useFreehandStroke({
    view,
    onTrace: (trace) => onDrawTrace?.(trace),
    onProblem: setProblem,
  });
  const stroke = freehandStroke.stroke;
  cancelStroke.current = freehandStroke.cancel;
  //  Held in a ref so `cancel` can stay a stable callback: the Escape handler
  //  depends on it, and re-registering that listener on every render is how a
  //  keypress ends up handled twice.
  const cancelBand = useRef<() => void>(() => undefined);
  const clearDraft = useRef<() => void>(() => undefined);
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

  const points = polygon.points;


  useEffect(() => {
    // Always listening: Escape clears a selection too, and a selection can
    // outlive every drawing mode.

    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') cancel();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [cancel]);


  const gestures = useCanvasGestures({
    view,
    setView,
    surface,
    spacing,
    drawing,
    band: { ...shapeBand, armed: shapeBand.armed },
    stroke: { ...freehandStroke, armed: tool === 'freehand' },
    addVertex: polygon.add,
    placing,
    onPlaceViewpoint,
    onViewpointPlaced: () => setPlacing(false),
  });

  return (
    <div className="canvas-wrap">
      {onDrawBed !== undefined && (
        <CanvasControls
          gridSpacingM={spacing}
          drawing={drawing}
          draftPoints={points.length}
          canUndo={polygon.canUndo}
          canRedo={polygon.canRedo}
          problem={problem}
          onZoomIn={() => zoom('in')}
          onZoomOut={() => zoom('out')}
          onFinish={polygon.finish}
          onCancel={cancel}
          onUndo={polygon.undo}
          onRedo={polygon.redo}
          placing={onPlaceViewpoint === undefined ? undefined : placing}
          onPlaceViewpoint={
            onPlaceViewpoint === undefined ? undefined : () => setPlacing((p) => !p)
          }
        />
      )}

      <svg
        ref={surface}
        data-testid="canvas-surface"
        className={
          drawing || tool !== null ? 'canvas canvas--drawing' : 'canvas'
        }
        viewBox={viewBox(view)}
        role="group"
        aria-label={`Gartenplan ${garden.name}, ${bedCount(garden.beds.length)}, ${obstacleCount(garden.obstacles.length)}`}
        onClick={gestures.onClick}
        onPointerDown={gestures.onPointerDown}
        onPointerMove={gestures.onPointerMove}
        onPointerUp={gestures.endDrag}
        onPointerLeave={gestures.endDrag}
      >
        <CanvasScene
          garden={garden}
          view={view}
          spacing={spacing}
          selectedBedId={selectedBedId}
          draft={points}
          viewpoint={viewpoint}
          onSelectBed={onSelectBed}
          onSelectObstacle={onSelectObstacle}
          palette={palette}
          armed={tool !== null}
        />
        <CanvasOverlays
          view={view}
          band={shapeBand.band}
          stroke={stroke}
          vertices={
            selected === null || selected.points === null || onReshapeObstacle === undefined
              ? null
              : {
                  points: vertexDrag.preview ?? selected.points,
                  origin: { x: selected.x, y: selected.y },
                  // A line has two ends rather than a closing edge; offering
                  // one would put a handle in mid-air between them.
                  closed: selected.shape !== 'line',
                  onChange: reshape,
                  onGrab: vertexDrag.grab,
                }
          }
          selectedBox={selectedBox}
          preview={preview}
          onGrab={onResizeObstacle === undefined ? null : grabHandle}
        />
      </svg>
    </div>
  );
}
