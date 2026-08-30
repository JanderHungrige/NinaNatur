import { useCallback, useEffect, useRef, useState } from 'react';

import type { GardenOut } from '../api/client';
import { type Box, type Handle, resizeBy, rotateBy } from '../canvas/handles';
import * as history from '../canvas/history';
import { tidy } from '../canvas/freehand';
import { isDegenerate, selfIntersects } from '../canvas/geometry';
import { snapPoint } from '../canvas/snap';
import {
  type Point,
  type Viewport,
  gridSpacing,
  panBy,
  toGarden,
  viewBox,
  zoomAt,
} from '../canvas/viewport';
import { beds as bedCount, obstacles as obstacleCount } from '../plural';
import { CanvasControls } from './CanvasControls';
import { CanvasScene } from './CanvasScene';
import { PreviewBox, ResizeHandles } from './ResizeHandles';

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
  /** The element the palette has armed, if any. A click then places one. */
  stampKind?: string | null;
  onPlaceStamp?: ((kind: string, x: number, y: number) => void) | undefined;
  /** The object wearing handles. Selection is the parent's, because the panel
   *  and the plan must agree on what is being edited. */
  selectedObstacleId?: number | null;
  onResizeObstacle?: ((obstacleId: number, box: Box) => void) | undefined;
}

const DEFAULT_SIZE = { widthPx: 800, heightPx: 600 };
const ZOOM_STEP = 1.6;

/** Two decimals: a viewpoint is a place someone stands, not a survey mark. */
const round = (v: number): number => Math.round(v * 100) / 100;

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
  stampKind = null,
  onPlaceStamp,
  selectedObstacleId = null,
  onResizeObstacle,
}: Props) {
  const [placing, setPlacing] = useState(false);
  const [view, setView] = useState<Viewport>({
    centreX: 0,
    centreY: 0,
    spanM: 40,
    ...(size ?? DEFAULT_SIZE),
  });
  const [drawing, setDrawing] = useState(false);
  /** Freehand mode, and the stroke being drawn in it.
   *
   * The points live in a ref and are mirrored into state for drawing. The ref
   * is what pointerup reads: state read from a render closure is one render
   * behind whenever events arrive faster than React re-renders, and losing the
   * last points of a stroke that way would be invisible until it wasn't. */
  const [freehand, setFreehand] = useState(false);
  const [stroke, setStroke] = useState<Point[] | null>(null);
  const strokePoints = useRef<Point[] | null>(null);
  const [draft, setDraft] = useState<history.History<Point[]>>(history.empty<Point[]>([]));
  const [problem, setProblem] = useState<string | null>(null);
  const surface = useRef<SVGSVGElement | null>(null);
  /**
   * The shape being dragged, shown as an outline until the pointer is let go.
   *
   * An outline rather than a live redraw of the object: the real footprint is
   * the server's to compute, and a second implementation of that arithmetic
   * here is a second thing to keep in step. draw.io shows a preview box for the
   * same reason.
   */
  const [preview, setPreview] = useState<Box | null>(null);
  const grab = useRef<{
    handle: Handle | 'rotate';
    startPx: { x: number; y: number };
    box: Box;
    moved: boolean;
  } | null>(null);

  const spacing = gridSpacing(view);
  const points = draft.present;

  useEffect(() => {
    if (size !== undefined) return undefined;
    const element = surface.current;
    if (element === null || typeof ResizeObserver === 'undefined') return undefined;
    const measure = () => {
      const rect = element.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return;
      setView((current) =>
        current.widthPx === rect.width && current.heightPx === rect.height
          ? current
          : { ...current, widthPx: rect.width, heightPx: rect.height },
      );
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [size]);

  const selected =
    garden.obstacles.find((o) => o.obstacle_id === selectedObstacleId) ?? null;
  /** A circle has no depth of its own; its diameter is both. */
  const selectedBox: Box | null =
    selected === null
      ? null
      : {
          x: selected.x,
          y: selected.y,
          width: selected.width,
          depth: selected.depth ?? selected.width,
          rotation: selected.rotation,
        };

  const metresPerPixel = view.spanM / view.widthPx;

  const grabHandle = (handle: Handle | 'rotate', event: React.PointerEvent) => {
    if (selectedBox === null) return;
    // The surface below would otherwise read this as a click on the plan, and
    // grabbing a handle would drop a bed corner or place a second house.
    event.stopPropagation();
    grab.current = {
      handle,
      startPx: { x: event.clientX, y: event.clientY },
      box: selectedBox,
      moved: false,
    };
    setPreview(selectedBox);
  };

  /**
   * The drag itself, on the window rather than on the handle: a pointer that
   * leaves the little square mid-gesture must keep resizing, which is what
   * makes a handle feel like a handle.
   */
  useEffect(() => {
    if (preview === null) return undefined;
    const onMove = (event: PointerEvent) => {
      const active = grab.current;
      if (active === null) return;
      const dxPx = event.clientX - active.startPx.x;
      const dyPx = event.clientY - active.startPx.y;
      if (dxPx !== 0 || dyPx !== 0) active.moved = true;

      if (active.handle === 'rotate') {
        const rect = surface.current?.getBoundingClientRect();
        const pointer = toGarden(
          { x: event.clientX - (rect?.left ?? 0), y: event.clientY - (rect?.top ?? 0) },
          view,
        );
        setPreview({
          ...active.box,
          rotation: rotateBy(active.box, pointer, { free: event.altKey }),
        });
        return;
      }
      // Screen y grows downward, garden y grows north.
      setPreview(
        resizeBy(
          active.box,
          active.handle,
          { dx: dxPx * metresPerPixel, dy: -dyPx * metresPerPixel },
          { keepSquare: selected?.shape === 'circle' },
        ),
      );
    };
    const onUp = () => {
      const active = grab.current;
      grab.current = null;
      const shape = preview;
      setPreview(null);
      // Clicking a handle is not a resize. Saving one anyway costs a PATCH and
      // a recomputation of every bed's light for a gesture that changed nothing.
      if (active === null || !active.moved || selected === null) return;
      onResizeObstacle?.(selected.obstacle_id, shape);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [preview, view, metresPerPixel, selected, onResizeObstacle]);

  const cancel = useCallback(() => {
    setDrawing(false);
    setFreehand(false);
    strokePoints.current = null;
    setStroke(null);
    setDraft(history.empty<Point[]>([]));
    setProblem(null);
  }, []);

  useEffect(() => {
    if (!drawing && !freehand) return undefined;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') cancel();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [drawing, freehand, cancel]);

  /**
   * Wheel zoom, anchored on the pointer so the garden stays where it was — but
   * only with Ctrl or Cmd held.
   *
   * A plain wheel over the canvas used to zoom, which meant the page could not
   * be scrolled past the plan at all: every scroll gesture was swallowed and
   * the view zoomed to its limit instead. Found by loading the page and letting
   * it scroll. Ctrl+wheel is also the browser's own zoom gesture, so it is the
   * one people already reach for, and the buttons remain the real control.
   */
  useEffect(() => {
    const element = surface.current;
    if (element === null) return undefined;
    const onWheel = (event: WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return; // let the page scroll
      event.preventDefault();
      const rect = element.getBoundingClientRect();
      setView((current) =>
        zoomAt(
          current,
          { x: event.clientX - rect.left, y: event.clientY - rect.top },
          event.deltaY > 0 ? ZOOM_STEP : 1 / ZOOM_STEP,
        ),
      );
    };
    element.addEventListener('wheel', onWheel, { passive: false });
    return () => element.removeEventListener('wheel', onWheel);
  }, []);

  /** Where a click landed, in garden metres. */
  const pointerMetres = (event: React.MouseEvent<SVGSVGElement>) => {
    const rect = surface.current?.getBoundingClientRect();
    return toGarden(
      { x: event.clientX - (rect?.left ?? 0), y: event.clientY - (rect?.top ?? 0) },
      view,
    );
  };

  /** Drag with the pointer to pan. Without it, zooming in strands the user. */
  const drag = useRef<{ x: number; y: number } | null>(null);

  const onPointerDown = (event: React.PointerEvent<SVGSVGElement>) => {
    if (drawing) return;
    if (freehand) {
      // Not also a pan. The same drag cannot both draw a line and slide the
      // garden out from under it.
      strokePoints.current = [pointerMetres(event)];
      setStroke(strokePoints.current);
      setProblem(null);
      return;
    }
    drag.current = { x: event.clientX, y: event.clientY };
  };

  const onPointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    if (strokePoints.current !== null) {
      strokePoints.current = [...strokePoints.current, pointerMetres(event)];
      setStroke(strokePoints.current);
      return;
    }
    const from = drag.current;
    if (from === null) return;
    drag.current = { x: event.clientX, y: event.clientY };
    setView((current) => panBy(current, event.clientX - from.x, event.clientY - from.y));
  };

  /**
   * The stroke ends. Everything the hand got wrong is fixed here rather than
   * complained about: the tremor is thinned out, a nearly-closed outline is
   * closed, and a stroke that crossed itself is untangled.
   *
   * The tolerances are in metres derived from the current zoom, so "close
   * enough" means the same distance on screen however far in the user is.
   */
  const endStroke = () => {
    const drawn = strokePoints.current;
    strokePoints.current = null;
    setStroke(null);
    if (drawn === null) return;
    setFreehand(false);
    const perPixel = view.spanM / view.widthPx;
    // Two pixels, but never finer than 10 cm however far the user has zoomed
    // in. Without the floor a close-up scribble stores a corner every few
    // millimetres — detail no gardener plants to, carried by every later
    // light computation. The floor matches the centimetre the outline is
    // rounded to.
    const shape = tidy(drawn, {
      tolerance: Math.max(0.1, perPixel * 2),
      closeWithin: Math.max(0.5, perPixel * 12),
    });
    if (shape === null) {
      setProblem('Der Umriss spannt keine Fläche auf — zieh eine geschlossene Form.');
      return;
    }
    onDrawBed?.(shape.map((p) => [p.x, p.y]));
  };

  const endDrag = () => {
    if (strokePoints.current !== null) {
      endStroke();
      return;
    }
    drag.current = null;
  };

  const addVertex = (event: React.MouseEvent<SVGSVGElement>) => {
    // Placing an armed element wins over drawing. Two modes share one click,
    // and without an order a click both places a house and drops a bed corner
    // underneath it.
    if (stampKind !== null && onPlaceStamp !== undefined) {
      const at = snapPoint(pointerMetres(event), spacing, { free: event.altKey });
      onPlaceStamp(stampKind, round(at.x), round(at.y));
      return;
    }
    if (placing && onPlaceViewpoint !== undefined) {
      const point = pointerMetres(event);
      onPlaceViewpoint(round(point.x), round(point.y));
      setPlacing(false);
      return;
    }
    if (!drawing) return;
    // Snap in metres, after the transform: snapping pixels first would store a
    // different coordinate at every zoom level.
    const metres = snapPoint(pointerMetres(event), spacing, { free: event.altKey });
    setDraft((current) => history.push(current, [...current.present, metres]));
    setProblem(null);
  };

  const finish = () => {
    // Order matters. A bow tie has zero *net* area, so a degeneracy check that
    // runs first tells someone their four-cornered shape needs three corners.
    // Most specific complaint first.
    if (points.length < 3) {
      setProblem('Ein Beet braucht mindestens drei Ecken.');
      return;
    }
    if (selfIntersects(points)) {
      setProblem('Der Umriss überschneidet sich selbst.');
      return;
    }
    if (isDegenerate(points)) {
      setProblem('Diese Ecken liegen auf einer Linie — sie spannen keine Fläche auf.');
      return;
    }
    onDrawBed?.(points.map((p) => [p.x, p.y]));
    cancel();
  };

  const zoom = (factor: number) =>
    setView((current) =>
      zoomAt(current, { x: current.widthPx / 2, y: current.heightPx / 2 }, factor),
    );

  return (
    <div className="canvas-wrap">
      {onDrawBed !== undefined && (
        <CanvasControls
          gridSpacingM={spacing}
          drawing={drawing}
          draftPoints={points.length}
          canUndo={history.canUndo(draft)}
          canRedo={history.canRedo(draft)}
          problem={problem}
          onZoomIn={() => zoom(1 / ZOOM_STEP)}
          onZoomOut={() => zoom(ZOOM_STEP)}
          onStartDrawing={() => setDrawing(true)}
          freehand={freehand}
          onStartFreehand={() => {
            setFreehand((on) => !on);
            setProblem(null);
          }}
          onFinish={finish}
          onCancel={cancel}
          onUndo={() => setDraft(history.undo)}
          onRedo={() => setDraft(history.redo)}
          placing={onPlaceViewpoint === undefined ? undefined : placing}
          onPlaceViewpoint={
            onPlaceViewpoint === undefined ? undefined : () => setPlacing((p) => !p)
          }
        />
      )}

      <svg
        ref={surface}
        data-testid="canvas-surface"
        className={drawing || freehand ? 'canvas canvas--drawing' : 'canvas'}
        viewBox={viewBox(view)}
        role="group"
        aria-label={`Gartenplan ${garden.name}, ${bedCount(garden.beds.length)}, ${obstacleCount(garden.obstacles.length)}`}
        onClick={addVertex}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerLeave={endDrag}
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
        {stroke !== null && stroke.length > 1 ? (
          <polyline
            data-testid="freehand-stroke"
            className="freehand-stroke"
            points={stroke.map((p) => `${p.x},${-p.y}`).join(' ')}
            strokeWidth={view.spanM / view.widthPx}
          />
        ) : null}
        {selectedBox !== null && onResizeObstacle !== undefined ? (
          <>
            {preview !== null ? <PreviewBox box={preview} view={view} /> : null}
            <ResizeHandles
              box={preview ?? selectedBox}
              view={view}
              onGrab={grabHandle}
            />
          </>
        ) : null}
      </svg>
    </div>
  );
}
