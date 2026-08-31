import { describe, expect, it, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

import { usePolygonDraft } from './usePolygonDraft';

function draft(closeWithin = 0.5) {
  const onShape = vi.fn();
  const onProblem = vi.fn();
  const hook = renderHook(() =>
    usePolygonDraft({ onShape, onProblem, onDone: vi.fn(), closeWithin }),
  );
  const add = (points: Array<[number, number]>) =>
    act(() => {
      for (const [x, y] of points) hook.result.current.add({ x, y });
    });
  return { onShape, onProblem, add, result: hook.result };
}

describe('usePolygonDraft — closing', () => {
  it('closes a triangle whose last corner lands near the first', () => {
    const { onShape, add, result } = draft();
    add([[0, 0], [4, 0], [0.2, 0.1]]);
    act(() => result.current.finish());
    expect(onShape).toHaveBeenCalled();
  });

  it('closes a quad whose last corner overlaps the first', () => {
    // The reported bug. Four corners where the last goes slightly past the
    // start make the outline self-intersect, and it was refused as a tangle —
    // when what the hand did was close the ring.
    const { onShape, onProblem, add, result } = draft();
    add([[0, 0], [4, 0], [4, 3], [-0.2, -0.15]]);
    act(() => result.current.finish());
    expect(onProblem).not.toHaveBeenCalledWith(expect.stringMatching(/überschneidet/));
    expect(onShape).toHaveBeenCalled();
    // The stray corner is dropped rather than kept: a polygon is closed by
    // being one, and a near-duplicate first corner is a zero-length edge.
    expect((onShape.mock.calls[0]?.[0] as number[][])).toHaveLength(3);
  });

  it('still refuses an outline that genuinely crosses itself', () => {
    const { onShape, onProblem, add, result } = draft();
    add([[0, 0], [4, 4], [4, 0], [0, 4]]);
    act(() => result.current.finish());
    expect(onShape).not.toHaveBeenCalled();
    expect(onProblem).toHaveBeenCalledWith(expect.stringMatching(/überschneidet/));
  });

  it('does not close a shape whose ends are genuinely apart', () => {
    const { onShape, add, result } = draft();
    add([[0, 0], [6, 0], [6, 4], [0, 4]]);
    act(() => result.current.finish());
    expect((onShape.mock.calls[0]?.[0] as number[][])).toHaveLength(4);
  });

  it('will not close its way below three corners', () => {
    const { onShape, onProblem, add, result } = draft();
    add([[0, 0], [3, 0], [0.1, 0.05]]);
    act(() => result.current.finish());
    // Dropping the last corner here would leave two, so it is kept and the
    // triangle stands.
    expect(onShape).toHaveBeenCalled();
    expect((onShape.mock.calls[0]?.[0] as number[][])).toHaveLength(3);
    expect(onProblem).not.toHaveBeenCalledWith(expect.stringMatching(/drei Ecken/));
  });
});
