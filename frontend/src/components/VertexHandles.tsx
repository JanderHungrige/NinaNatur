import { insertVertex, midpoints, moveVertex, removeVertex } from '../canvas/vertices';
import type { Viewport } from '../canvas/viewport';

interface Props {
  /** Points in metres relative to the element's own (x, y). */
  points: number[][];
  origin: { x: number; y: number };
  view: Viewport;
  /** Whether the last point joins back to the first. False for a path. */
  closed: boolean;
  onChange: (points: number[][]) => void;
  onGrabVertex: (index: number, event: React.PointerEvent) => void;
}

/**
 * The corners of an outline, and the places a new one can go.
 *
 * Corners are squares and the insertion points are smaller diamonds, so the two
 * are told apart without reading a legend — the same distinction every
 * flowchart tool draws.
 */
export function VertexHandles({
  points,
  origin,
  view,
  closed,
  onChange,
  onGrabVertex,
}: Props) {
  const scale = view.spanM / view.widthPx;
  const size = 10 * scale;

  return (
    <g className="vertices" aria-hidden="true">
      {midpoints(points, { closed }).map(({ index, at }) => (
        <rect
          key={`mid-${index}`}
          data-testid={`vertex-add-${index}`}
          className="vertex vertex--add"
          x={origin.x + at[0] - size / 3}
          y={-(origin.y + at[1]) - size / 3}
          width={(size * 2) / 3}
          height={(size * 2) / 3}
          transform={`rotate(45 ${origin.x + at[0]} ${-(origin.y + at[1])})`}
          onClick={() => onChange(insertVertex(points, index))}
        />
      ))}
      {points.map((p, index) => (
        <rect
          key={`vertex-${index}`}
          data-testid={`vertex-${index}`}
          className="vertex"
          x={origin.x + p[0]! - size / 2}
          y={-(origin.y + p[1]!) - size / 2}
          width={size}
          height={size}
          onPointerDown={(event) => onGrabVertex(index, event)}
          onDoubleClick={() => {
            // Refused rather than silently ignored: below three corners the
            // element would still exist and cover nothing.
            const fewer = removeVertex(points, index);
            if (fewer !== null) onChange(fewer);
          }}
        />
      ))}
    </g>
  );
}

export { moveVertex };
