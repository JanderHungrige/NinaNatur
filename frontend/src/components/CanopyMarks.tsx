import type { CanopySuggestion } from '../api/client';

interface Props {
  trees: CanopySuggestion[];
}

/**
 * Where the found trees stand (doc 89): each suggestion's crown as a dashed ring
 * on the plan, from its position and radius and nothing else.
 *
 * A mark, not an object (doc 84). It is hidden from the accessibility tree and
 * from the pointer, so it never takes a click from the bed or path beneath it;
 * the plan's controls say how many there are, and the card in the details is
 * where one is accepted or refused.
 */
export function CanopyMarks({ trees }: Props) {
  if (trees.length === 0) return null;

  return (
    <g className="canopy-marks" aria-hidden="true" pointerEvents="none">
      {trees.map((tree) => (
        <circle
          key={tree.suggestion_id}
          className="canopy-mark"
          cx={tree.x}
          cy={-tree.y}
          r={tree.radius_m}
        />
      ))}
    </g>
  );
}
