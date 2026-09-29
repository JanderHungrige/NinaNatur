import type { ShadowMark } from '../api/client';

interface Props {
  marks: ShadowMark[];
}

/** Half a cross's arm, in garden metres: the viewpoint's dot is 0.35 round. */
const ARM_M = 0.3;

/**
 * Where the gardener saw shadows end, and where the model ends them (doc 122).
 *
 * Each mark is a cross; the model's shadow of its thing at its moment is a
 * dashed outline, and a line runs from the cross to that outline's nearest
 * point — the way the reading measures. The cross and the line lie on a halo
 * of the paper's colour, so they read over the sun map's darkest shade.
 * Drawn above the shapes and never a target: a click through it still
 * reaches the plan.
 */
export function ShadowMarkLayer({ marks }: Props) {
  if (marks.length === 0) return null;
  return (
    <g className="shadow-marks" pointerEvents="none" aria-hidden="true">
      {marks.map((mark) => (
        <g key={mark.mark_id} className="shadow-mark" data-mark-id={mark.mark_id}>
          {mark.reading !== null && (
            <>
              <path className="shadow-mark__edge"
                    d={mark.reading.rings.map((ring) => outline(ring)).join('')} />
              <path className="shadow-mark__halo" d={way(mark, mark.reading.nearest)} />
              <path className="shadow-mark__way" d={way(mark, mark.reading.nearest)} />
            </>
          )}
          <path className="shadow-mark__halo" d={cross(mark)} />
          <path className="shadow-mark__cross" d={cross(mark)} />
        </g>
      ))}
    </g>
  );
}

/** A cross over the mark, in plan coordinates: y is drawn downwards. */
function cross(mark: ShadowMark): string {
  const x = mark.x;
  const y = -mark.y;
  return `M${x - ARM_M},${y - ARM_M}L${x + ARM_M},${y + ARM_M}`
    + `M${x - ARM_M},${y + ARM_M}L${x + ARM_M},${y - ARM_M}`;
}

/** From the mark to the model's nearest edge point. */
function way(mark: ShadowMark, nearest: number[]): string {
  return `M${mark.x},${-mark.y}L${nearest[0] ?? mark.x},${-(nearest[1] ?? mark.y)}`;
}

function outline(ring: number[][]): string {
  return ring.map((point, i) => `${i === 0 ? 'M' : 'L'}${point[0]},${-(point[1] ?? 0)}`).join('')
    + 'Z';
}
