import { useCallback, useEffect, useRef, useState } from 'react';

import type { GardenOut } from '../api/client';
import { type Box, boxOf } from '../canvas/handles';
import { useHandleDrag } from '../canvas/useHandleDrag';
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
  /** The object wearing handles. Selection is the parent's, because the panel
   *  and the plan must agree on what is being edited. */
  selectedObstacleId?: number | null;
  onResizeObstacle?: ((obstacleId: number, box: Box) => void) | undefined;
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
}: Props) {
  const { view, setView, surface, zoom } = useViewport(size);
  const [placing, setPlacing] = useState(false);

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
  const [drawing, setDrawing] = useState(false);
  /** Freehand mode, and the stroke being drawn in it.
   *
   * The points live in a ref and are mirrored into state for drawing. The ref
   * is what pointerup reads: state read from a render closure is one render
   * behind whenever events arrive faster than React re-renders, and losing the
   * last points of a stroke that way would be invisible until it wasn't. */
  const [freehand, setFreehand] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const freehandStroke = useFreehandStroke({
    view,
    onShape: (polygon) => onDrawBed?.(polygon),
    onProblem: setProblem,
    onDone: () => setFreehand(false),
  });
  const stroke = freehandStroke.stroke;
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
  });
  clearDraft.current = polygon.clear;

  /** Leave every drawing mode and forget what was half-drawn. Stable, because
   *  the Escape listener depends on it and re-registering that on every render
   *  is how one keypress ends up handled twice. */
  const cancel = useCallback(() => {
    setDrawing(false);
    setFreehand(false);
    cancelBand.current();
    clearDraft.current();
    setProblem(null);
  }, []);

  const spacing = gridSpacing(view);
  const points = polygon.points;


  useEffect(() => {
    if (!drawing && !freehand && !shapeBand.active) return undefined;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') cancel();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [drawing, freehand, shapeBand.active, cancel]);


  const gestures = useCanvasGestures({
    view,
    setView,
    surface,
    spacing,
    drawing,
    band: { ...shapeBand, armed: shapeBand.armed },
    stroke: { ...freehandStroke, armed: freehand },
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
          onStartDrawing={() => setDrawing(true)}
          freehand={freehand}
          onStartFreehand={() => {
            setFreehand((on) => !on);
            setProblem(null);
          }}
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
          drawing || freehand || shapeBand.armed ? 'canvas canvas--drawing' : 'canvas'
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
        />
        <CanvasOverlays
          view={view}
          band={shapeBand.band}
          stroke={stroke}
          selectedBox={selectedBox}
          preview={preview}
          onGrab={onResizeObstacle === undefined ? null : grabHandle}
        />
      </svg>
    </div>
  );
}
