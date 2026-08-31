/**
 * A polygon drawn corner by corner, and the complaints it can earn.
 *
 * The last of the gestures split out of GardenCanvas. The order of the checks
 * in `finish` is the load-bearing part: a bow tie has zero *net* area, so a
 * degeneracy test that runs first tells somebody their four-cornered shape
 * needs three corners.
 */
import { useState } from 'react';

import { isDegenerate, selfIntersects } from './geometry';
import * as history from './history';
import type { Point } from './viewport';

interface Options {
  onShape: (polygon: number[][]) => void;
  onProblem: (message: string | null) => void;
  onDone: () => void;
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
    // Order matters. A bow tie has zero *net* area, so a degeneracy check that
    // runs first tells someone their four-cornered shape needs three corners.
    // Most specific complaint first.
    if (points.length < 3) {
      options.onProblem('Ein Beet braucht mindestens drei Ecken.');
      return;
    }
    if (selfIntersects(points)) {
      options.onProblem('Der Umriss überschneidet sich selbst.');
      return;
    }
    if (isDegenerate(points)) {
      options.onProblem('Diese Ecken liegen auf einer Linie — sie spannen keine Fläche auf.');
      return;
    }
    options.onShape(points.map((p) => [p.x, p.y]));
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
