import { type Box, HANDLES, type Handle, handleAt } from '../canvas/handles';
import type { Viewport } from '../canvas/viewport';

interface Props {
  box: Box;
  view: Viewport;
  onGrab: (handle: Handle | 'rotate', event: React.PointerEvent) => void;
}

/** Metres per pixel, so a handle is the same size on screen at every zoom. */
function metresPerPixel(view: Viewport): number {
  return view.spanM / view.widthPx;
}

/** How far above the object the rotation handle floats, in pixels. */
const ROTATE_OFFSET_PX = 28;

/**
 * The eight resize grips and the rotation grip, in the manner of draw.io.
 *
 * Sized in pixels converted to metres rather than in metres: a grip fixed at
 * 0.3 m is invisible on a whole-garden view and swallows the object on a close
 * one. The user is aiming with a pointer, so the target belongs in the
 * pointer's unit.
 */
export function ResizeHandles({ box, view, onGrab }: Props) {
  const scale = metresPerPixel(view);
  // Twelve, not eight: the smaller grips were there all along and nobody
  // found them, which is the same as their not being there.
  const size = 12 * scale;
  const rotateAt = handleAt(box, 'n');
  const lift = ROTATE_OFFSET_PX * scale;

  return (
    <g className="handles" aria-hidden="true">
      {HANDLES.map((handle) => {
        const at = handleAt(box, handle);
        return (
          <rect
            key={handle}
            data-testid={`handle-${handle}`}
            className="handle"
            x={at.x - size / 2}
            // Screen y grows downward while garden y grows north, so the sign
            // flips here as it does everywhere else on this canvas.
            y={-at.y - size / 2}
            width={size}
            height={size}
            onPointerDown={(event) => onGrab(handle, event)}
          />
        );
      })}
      <line
        className="handle__tether"
        x1={rotateAt.x}
        y1={-rotateAt.y}
        x2={rotateAt.x}
        y2={-rotateAt.y - lift}
        strokeWidth={scale}
      />
      <circle
        data-testid="handle-rotate"
        className="handle handle--rotate"
        cx={rotateAt.x}
        cy={-rotateAt.y - lift}
        r={size * 0.7}
        onPointerDown={(event) => onGrab('rotate', event)}
      />
    </g>
  );
}

/**
 * The outline of a shape mid-drag.
 *
 * A rotated rectangle even for a circle: it is the box being resized, and
 * showing the box is what tells the user what the handles are doing.
 */
export function PreviewBox({ box, view }: { box: Box; view: Viewport }) {
  const corners = (['nw', 'ne', 'se', 'sw'] as const)
    .map((handle) => handleAt(box, handle))
    .map((p) => `${p.x},${-p.y}`)
    .join(' ');
  return (
    <polygon
      data-testid="resize-preview"
      className="handle__preview"
      points={corners}
      strokeWidth={metresPerPixel(view)}
    />
  );
}
