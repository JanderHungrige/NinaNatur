import { useCallback, useMemo, useState } from 'react';

import type { GardenOut } from '../api/client';
import { type Picked, resolveSelection, selectedIds } from './selection';

/**
 * The one selection in a garden (doc 88): what is picked, what that is, and the
 * ids the plan draws it with.
 *
 * The plan, the element list and the details all read this, and nothing else
 * holds a piece of it. Five pieces of state used to, and they disagreed: a bed
 * chosen in the list lost its handles, and an element chosen after a bed left
 * the bed marked.
 */
export function useSelection(garden: GardenOut) {
  const [picked, setPicked] = useState<Picked>(null);
  /** An element asked about from the plan, whose form is to take the focus. */
  const [askedFor, setAskedFor] = useState<number | null>(null);

  const selection = useMemo(() => resolveSelection(garden, picked), [garden, picked]);
  const ids = useMemo(() => selectedIds(selection), [selection]);

  const selectElement = useCallback((id: number) => setPicked({ what: 'element', id }), []);
  const selectPlanting = useCallback((id: number) => setPicked({ what: 'planting', id }), []);

  const clear = useCallback(() => {
    setPicked(null);
    setAskedFor(null);
  }, []);

  /** Right-click, Shift+F10 or the context-menu key (doc 51): the element is
   *  selected, and its form takes the focus. */
  const askAbout = useCallback((id: number) => {
    setPicked({ what: 'element', id });
    setAskedFor(id);
  }, []);

  const focusTaken = useCallback(() => setAskedFor(null), []);

  return { selection, ids, selectElement, selectPlanting, clear, askAbout, askedFor, focusTaken };
}
