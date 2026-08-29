/**
 * Undo and redo over any state.
 *
 * A drawing tool without undo is a tool people are afraid to use, and a timid
 * user draws nothing. Kept generic and pure so the rules can be tested without
 * a canvas.
 */

export interface History<T> {
  past: T[];
  present: T;
  future: T[];
}

/**
 * A drawing session is long and every placed vertex is a state, so the past is
 * bounded. The oldest states are dropped, never the newest.
 */
const LIMIT = 200;

export function empty<T>(present: T): History<T> {
  return { past: [], present, future: [] };
}

export function push<T>(history: History<T>, present: T): History<T> {
  const past = [...history.past, history.present].slice(-LIMIT);
  // Drawing something new abandons the redo branch. The alternative is a tree,
  // and nobody navigates a tree with one keyboard shortcut.
  return { past, present, future: [] };
}

export function canUndo<T>(history: History<T>): boolean {
  return history.past.length > 0;
}

export function canRedo<T>(history: History<T>): boolean {
  return history.future.length > 0;
}

export function undo<T>(history: History<T>): History<T> {
  // Ctrl+Z on an untouched drawing is a normal thing for a person to do.
  if (!canUndo(history)) return history;
  const previous = history.past[history.past.length - 1] as T;
  return {
    past: history.past.slice(0, -1),
    present: previous,
    future: [history.present, ...history.future],
  };
}

export function redo<T>(history: History<T>): History<T> {
  if (!canRedo(history)) return history;
  const next = history.future[0] as T;
  return {
    past: [...history.past, history.present].slice(-LIMIT),
    present: next,
    future: history.future.slice(1),
  };
}
