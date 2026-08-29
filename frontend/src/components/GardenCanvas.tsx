import { useCallback, useEffect, useRef, useState } from 'react';

import type { GardenOut } from '../api/client';
import * as history from '../canvas/history';
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
}

const DEFAULT_SIZE = { widthPx: 800, heightPx: 600 };
const ZOOM_STEP = 1.6;

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
}: Props) {
  const [view, setView] = useState<Viewport>({
    centreX: 0,
    centreY: 0,
    spanM: 40,
    ...(size ?? DEFAULT_SIZE),
  });
  const [drawing, setDrawing] = useState(false);
  const [draft, setDraft] = useState<history.History<Point[]>>(history.empty<Point[]>([]));
  const [problem, setProblem] = useState<string | null>(null);
  const surface = useRef<SVGSVGElement | null>(null);

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

  const cancel = useCallback(() => {
    setDrawing(false);
    setDraft(history.empty<Point[]>([]));
    setProblem(null);
  }, []);

  useEffect(() => {
    if (!drawing) return undefined;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') cancel();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [drawing, cancel]);

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

  /** Drag with the pointer to pan. Without it, zooming in strands the user. */
  const drag = useRef<{ x: number; y: number } | null>(null);

  const onPointerDown = (event: React.PointerEvent<SVGSVGElement>) => {
    if (drawing) return;
    drag.current = { x: event.clientX, y: event.clientY };
  };

  const onPointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    const from = drag.current;
    if (from === null) return;
    drag.current = { x: event.clientX, y: event.clientY };
    setView((current) => panBy(current, event.clientX - from.x, event.clientY - from.y));
  };

  const endDrag = () => {
    drag.current = null;
  };

  const addVertex = (event: React.MouseEvent<SVGSVGElement>) => {
    if (!drawing) return;
    const rect = surface.current?.getBoundingClientRect();
    const at = {
      x: event.clientX - (rect?.left ?? 0),
      y: event.clientY - (rect?.top ?? 0),
    };
    // Snap in metres, after the transform: snapping pixels first would store a
    // different coordinate at every zoom level.
    const metres = snapPoint(toGarden(at, view), spacing, { free: event.altKey });
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
          onFinish={finish}
          onCancel={cancel}
          onUndo={() => setDraft(history.undo)}
          onRedo={() => setDraft(history.redo)}
        />
      )}

      <svg
        ref={surface}
        data-testid="canvas-surface"
        className={drawing ? 'canvas canvas--drawing' : 'canvas'}
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
          onSelectBed={onSelectBed}
          onSelectObstacle={onSelectObstacle}
        />
      </svg>
    </div>
  );
}
