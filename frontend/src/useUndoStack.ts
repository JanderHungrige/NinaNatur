import { useCallback, useEffect, useRef, useState } from 'react';

export interface UndoEntry {
  /** What is being taken back, said the way the status line says it. */
  label: string;
  undo: () => Promise<void>;
}

/**
 * The last few drawing actions, and how to take each one back.
 *
 * Inverses rather than snapshots. A snapshot of the whole garden would have to
 * be replayed against the server call by call to be restored, and the server is
 * the only thing that knows what a resize did to the light. An inverse is one
 * call — move back by the same amount, put the old points back, delete what was
 * just drawn.
 *
 * Bounded, because an unbounded stack of closures holds every garden this
 * session ever saw. Ten is more than anyone reaches for.
 */
const DEPTH = 10;

export function useUndoStack(): {
  remember: (entry: UndoEntry) => void;
  undo: () => Promise<UndoEntry | null>;
  forget: () => void;
  depth: number;
} {
  const stack = useRef<UndoEntry[]>([]);
  // Mirrored into state only so a button can be disabled; the ref is what the
  // keyboard handler reads, because a handler registered once would otherwise
  // close over the stack as it was at registration.
  const [depth, setDepth] = useState(0);

  const remember = useCallback((entry: UndoEntry) => {
    stack.current = [...stack.current, entry].slice(-DEPTH);
    setDepth(stack.current.length);
  }, []);

  const undo = useCallback(async () => {
    const entry = stack.current.at(-1);
    if (entry === undefined) return null;
    stack.current = stack.current.slice(0, -1);
    setDepth(stack.current.length);
    await entry.undo();
    return entry;
  }, []);

  const forget = useCallback(() => {
    stack.current = [];
    setDepth(0);
  }, []);

  return { remember, undo, forget, depth };
}

/**
 * Ctrl+Z, and Cmd+Z where that is the key.
 *
 * Not while a text field has focus: the browser's own undo is what somebody
 * mid-sentence in a label field means, and taking a rectangle back instead
 * would be the wrong answer to the right key.
 */
export function useUndoShortcut(undo: () => void, enabled: boolean): void {
  useEffect(() => {
    if (!enabled) return;
    const onKey = (event: KeyboardEvent) => {
      const undoKey = (event.ctrlKey || event.metaKey) && !event.shiftKey
        && event.key.toLowerCase() === 'z';
      if (!undoKey || isTyping(event.target)) return;
      event.preventDefault();
      undo();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [undo, enabled]);
}

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  return ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName);
}
