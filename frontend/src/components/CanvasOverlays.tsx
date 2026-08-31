import type { Band } from '../canvas/useShapeBand';
import type { Box } from '../canvas/handles';
import type { Handle } from '../canvas/handles';
import type { Point, Viewport } from '../canvas/viewport';
import { PreviewBox, ResizeHandles } from './ResizeHandles';
import { VertexHandles } from './VertexHandles';

interface Props {
  view: Viewport;
  /** The selected element's own outline, when it has one to edit. */
  vertices: {
    points: number[][];
    origin: { x: number; y: number };
    closed: boolean;
    onChange: (points: number[][]) => void;
    onGrab: (index: number, event: React.PointerEvent) => void;
  } | null;
  band: Band | null;
  stroke: Point[] | null;
  selectedBox: Box | null;
  preview: Box | null;
  onGrab: ((handle: Handle | 'rotate', event: React.PointerEvent) => void) | null;
}

/**
 * What is drawn on top of the plan while a gesture is in progress.
 *
 * Split out of GardenCanvas because it is the half that has no state of its
 * own: everything here is a function of what the gesture hooks are holding, and
 * reading it should not mean scrolling past three pointer handlers.
 */
export function CanvasOverlays({
  view,
  vertices,
  band,
  stroke,
  selectedBox,
  preview,
  onGrab,
}: Props) {
  const perPixel = view.spanM / view.widthPx;
  return (
    <>
        {band !== null ? (
          <rect
            data-testid="shape-preview"
            className="shape-preview"
            x={Math.min(band.from.x, band.to.x)}
            y={-Math.max(band.from.y, band.to.y)}
            width={Math.abs(band.to.x - band.from.x)}
            height={Math.abs(band.to.y - band.from.y)}
            strokeWidth={perPixel}
          />
        ) : null}
        {stroke !== null && stroke.length > 1 ? (
          <polyline
            data-testid="freehand-stroke"
            className="freehand-stroke"
            points={stroke.map((p) => `${p.x},${-p.y}`).join(' ')}
            strokeWidth={perPixel}
          />
        ) : null}
        {selectedBox !== null && onGrab !== null ? (
          <>
            {preview !== null ? <PreviewBox box={preview} view={view} /> : null}
            <ResizeHandles
              box={preview ?? selectedBox}
              view={view}
              onGrab={onGrab}
            />
          </>
        ) : null}
      {vertices !== null ? (
        <VertexHandles
          points={vertices.points}
          origin={vertices.origin}
          view={view}
          closed={vertices.closed}
          onChange={vertices.onChange}
          onGrabVertex={vertices.onGrab}
        />
      ) : null}
    </>
  );
}
