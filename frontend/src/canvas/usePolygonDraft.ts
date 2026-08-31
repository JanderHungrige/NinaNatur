/**
 * A polygon drawn corner by corner, and the complaints it can earn.
 *
 * The last of the gestures split out of GardenCanvas. The order of the checks
 * in `finish` is the load-bearing part: a bow tie has zero *net* area, so a
 * degeneracy test that runs first tells somebody their four-cornered shape
 * needs three corners.
 */
import { useState } from 'react';

import { closeIfNear } from './freehand';
import { isDegenerate, selfIntersects } from './geometry';
import * as history from './history';
import type { Point } from './viewport';

interface Options {
  onShape: (polygon: number[][]) => void;
  onProblem: (message: string | null) => void;
  onDone: () => void;
  /** How near the first corner the last one has to land to count as closing. */
  closeWithin: number;
}

export function usePolygonDraft(options: Options) {
  const [draft, setDraft] = useState<history.History<Point[]>>(history.empty<Point[]>([]));
  const points = draft.present;

  const add = (at: Point) => {
    setDraft((current) => history.push(current, [...current.present, at]));
    options.onProblem(null);
  };

  const clear = () => setDraft(history.empty<Point[]>([]));

  const finish = () => {
    // Closing before the checks, because an overlap at the start is a closure
    // and not a tangle. Four corners where the last goes slightly past the
    // first make the outline self-intersect, and it was refused as crossing
    // itself — which is not what the hand was doing.
    const outline = closeIfNear(points, options.closeWithin);
    // Order matters. A bow tie has zero *net* area, so a degeneracy check that
    // runs first tells someone their four-cornered shape needs three corners.
    // Most specific complaint first.
    if (outline.length < 3) {
      options.onProblem('Ein Beet braucht mindestens drei Ecken.');
      return;
    }
    if (selfIntersects(outline)) {
      options.onProblem('Der Umriss überschneidet sich selbst.');
      return;
    }
    if (isDegenerate(outline)) {
      options.onProblem('Diese Ecken liegen auf einer Linie — sie spannen keine Fläche auf.');
      return;
    }
    options.onShape(outline.map((p) => [p.x, p.y]));
    options.onDone();
  };

  return {
    points,
    draft,
    add,
    clear,
    finish,
    undo: () => setDraft(history.undo),
    redo: () => setDraft(history.redo),
    canUndo: history.canUndo(draft),
    canRedo: history.canRedo(draft),
  };
}
