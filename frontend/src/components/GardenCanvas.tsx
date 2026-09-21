import { useRef } from 'react';

import type { Cluster } from '../canvas/clusters';
import { elementById } from '../canvas/elements';
import { type Box, boxOf } from '../canvas/handles';
import { useCanvasGestures } from '../canvas/useCanvasGestures';
import { useClusterDrag } from '../canvas/useClusterDrag';
import { useDrawingModes } from '../canvas/useDrawingModes';
import { useElementDrag } from '../canvas/useElementDrag';
import { useHandleDrag } from '../canvas/useHandleDrag';
import { useStableHandlers } from '../canvas/useStableHandlers';
import { useVertexDrag } from '../canvas/useVertexDrag';
import { useViewport } from '../canvas/useViewport';
import { type Point, gridSpacing, panBy, viewBox, zoomAt } from '../canvas/viewport';
import { isFixed } from '../kinds';
import { beds as bedCount, obstacles as obstacleCount } from '../plural';
import { usePinch } from '../usePinch';
import { CanvasControls } from './CanvasControls';
import { CanvasOverlays } from './CanvasOverlays';
import { CanvasScene } from './CanvasScene';
import { PlanCredit } from './PlanCredit';
import { PlanFurniture } from './PlanFurniture';
import { SunReadout, type SunReadoutHandle } from './SunReadout';
import type { GardenCanvasProps } from './GardenCanvasProps';

/** One empty list, not a new one per render: the scene is memoised on it. */
const NO_CLUSTERS: Cluster[] = [];

/**
 * The garden plan, and the surface it is drawn on.
 *
 * SVG rather than <canvas>: every bed and obstacle is a real DOM node, so it can
 * be focused, named and found by a test, and the scene is tens of shapes rather
 * than thousands. The arithmetic lives in ../canvas, where it can be tested
 * without rendering anything.
 *
 * What it is given is `GardenCanvasProps`, and its drawing modes are
 * `useDrawingModes` — both split out when houses, streets and two fingers came
 * in (doc 87, B1; doc 91, B1), to keep this file under the 300-line rule.
 */
export function GardenCanvas({
  garden,
  hint,
  selectedBedId,
  onSelectBed,
  size,
  onDrawBed,
  onSelectObstacle,
  clusters,
  selectedPlantingId = null,
  freshPlantingId = null,
  onSelectCluster,
  onMoveCluster,
  onShowClusterInfo,
  sunMap,
  terrain, landcover,
  shadows,
  viewpoint = null,
  onPlaceViewpoint,
  canopies,
  onShowFoundTrees,
  selectedObstacleId = null,
  onResizeObstacle,
  tool = null,
  onDrawShape,
  onDrawTrace,
  onCancelTool,
  onClearSelection,
  onAskWhatItIs,
  onMoveObstacle,
  onReshapeObstacle,
}: GardenCanvasProps) {
  // Set while two fingers pinch, so Safari's own gesture does not zoom as well.
  const touchPinch = useRef(false);
  const { view, setView, surface, stage, zoom, moving } = useViewport(size, touchPinch);
  const readout = useRef<SunReadoutHandle>(null);
  // The same functions from render to render, or the memoised scene redraws.
  const handlers = useStableHandlers({
    onSelectBed, onSelectObstacle, onSelectCluster, onShowClusterInfo, onAskWhatItIs,
  });

  // Placing a viewpoint is the rail's Standpunkt (doc 89), not a mode of the plan's own.
  const placing = tool === 'viewpoint';
  const spacing = gridSpacing(view);
  const elementDrag = useElementDrag({
    view,
    surface,
    // Houses, streets and the ground stay where they are, and a finger moves
    // only what has been chosen (doc 87, B1). A refused grab pans the plan: on
    // a phone most of it is houses, streets and beds.
    movable: (id, byFinger) =>
      !isFixed(elementById(garden, id)?.kind ?? '') &&
      (!byFinger || id === selectedObstacleId || id === selectedBedId),
    onFinish: (id, by) => onMoveObstacle?.(id, by),
  });

  // Both arrays. A bed is an element of kind `bed`, and looking only in
  // `obstacles` is what took a bed's handles away the moment it was labelled.
  const selected = elementById(garden, selectedObstacleId);
  const fixed = selected !== null && isFixed(selected.kind);

  // Which bed a patch is in, so a drag can be clamped to that outline. Looked
  // up rather than carried on the cluster: the outline is the bed's, and two
  // copies of it drift the moment the bed is reshaped.
  const bedOf = (plantingId: number): Point[] | null => {
    const bed = garden.beds.find((b) =>
      b.plantings.some((p) => p.planting_id === plantingId),
    );
    return bed === undefined
      ? null
      : bed.polygon.map((p) => ({ x: p[0] ?? 0, y: p[1] ?? 0 }));
  };
  const clusterDrag = useClusterDrag({
    view,
    surface,
    clusters: clusters ?? NO_CLUSTERS,
    bedOf,
    // As with shapes: a finger moves only the patch that has been chosen.
    movable: (plantingId, byFinger) => !byFinger || plantingId === selectedPlantingId,
    onFinish: (plantingId, to) => onMoveCluster?.(plantingId, to),
  });
  // Derived rather than stored: Wave 11 keeps points, and the box the handles
  // work in is read back off them. What stays put has no box, so no handles.
  const selectedBox: Box | null = selected === null || fixed ? null : boxOf(selected);
  const { preview, grabHandle } = useHandleDrag({
    selectedBox,
    keepSquare: selected?.shape === 'circle',
    view,
    surface,
    onFinish: (box) => {
      if (selected !== null) onResizeObstacle?.(selected.id, box);
    },
  });
  const reshape = (points: number[][]) => {
    if (selected !== null) onReshapeObstacle?.(selected.id, points);
  };
  const vertexDrag = useVertexDrag({
    points: selected?.points ?? null,
    origin: { x: selected?.x ?? 0, y: selected?.y ?? 0 },
    view,
    surface,
    onFinish: reshape,
  });

  const { drawing, problem, freehandStroke, stroke, shapeBand, polygon, cancel } = useDrawingModes({
    tool,
    view,
    onDrawBed,
    onDrawShape,
    onDrawTrace,
    onCancelTool,
    onClearSelection,
  });
  const points = polygon.points;

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
    // Placed once, the tool is put down, as the button used to switch itself off.
    onViewpointPlaced: () => onCancelTool?.(),
    moving,
  });
  // Two fingers zoom the plan between them and move it with them (doc 91, B1).
  // Whatever one finger was doing ends when the second lands.
  const pinch = usePinch({
    onStart: () => {
      gestures.cancelPan();
      elementDrag.cancel();
      clusterDrag.cancel();
      touchPinch.current = true;
      moving.start();
    },
    onChange: ({ scale, at, moved }) =>
      setView((current) => panBy(zoomAt(current, at, 1 / scale), moved.x, moved.y)),
    onEnd: () => {
      touchPinch.current = false;
      moving.stop();
    },
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
          foundTrees={canopies?.length ?? 0}
          onShowFoundTrees={onShowFoundTrees}
        />
      )}

      {/* Its own positioning context, because the readout is placed in pixels
          from the *drawing*'s top left and the controls row above it is not
          part of that measurement. And the box that is measured: its height
          comes from the page, never from the drawing inside it (doc 86). */}
      <div className="canvas-stage" ref={stage}>
      <SunReadout ref={readout} map={sunMap?.map} view={view} surface={surface} />

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
        // A pan begun on a shape ends in a click on it; that click is not a choice.
        onClickCapture={gestures.onClickCapture}
        onPointerDown={gestures.onPointerDown}
        {...pinch}
        onPointerMove={(event) => {
          gestures.onPointerMove(event);
          // Nothing under a moving plan is worth reading out.
          if (gestures.isPanning()) readout.current?.clear();
          else readout.current?.read(event);
        }}
        onPointerUp={gestures.endDrag}
        onPointerLeave={() => {
          gestures.endDrag();
          readout.current?.clear();
        }}
      >
        <CanvasScene
          garden={garden}
          view={view}
          spacing={spacing}
          selectedBedId={selectedBedId}
          draft={points}
          viewpoint={viewpoint}
          canopies={canopies}
          onSelectBed={handlers.onSelectBed}
          onSelectObstacle={handlers.onSelectObstacle}
          clusters={clusterDrag.shown}
          selectedPlantingId={selectedPlantingId}
          freshPlantingId={freshPlantingId}
          selectedObstacleId={selectedObstacleId}
          onSelectCluster={handlers.onSelectCluster}
          onGrabCluster={clusterDrag.grab}
          onShowClusterInfo={handlers.onShowClusterInfo}
          sunMap={sunMap}
          terrain={terrain} landcover={landcover}
          shadows={shadows}
          armed={tool !== null}
          onAskWhatItIs={handlers.onAskWhatItIs}
          onGrabElement={onMoveObstacle === undefined ? undefined : elementDrag.grab}
          dragOffset={elementDrag.offset}
        />
        <CanvasOverlays
          view={view}
          band={shapeBand.band}
          stroke={stroke}
          vertices={
            selected === null || fixed || selected.points === null || onReshapeObstacle === undefined
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
      <PlanFurniture metresPerPixel={view.spanM / view.widthPx} title={garden.name}
                     updatedAt={garden.updated_at} />
      {hint !== undefined && <p className="plan-hint" aria-live="polite">{hint}</p>}
      </div>
      <PlanCredit garden={garden} landcover={(landcover?.areas.length ?? 0) > 0} />
    </div>
  );
}
