import { useCallback } from 'react';

import type { GardenOut, NinaNaturClient } from '../api/client';
import { useUndoShortcut, useUndoStack } from '../useUndoStack';
import type { Status } from '../useStatus';
import { useClipboard } from './useClipboard';
import { useDerived } from './useDerived';
import { useElements } from './useElements';
import { useGeometry } from './useGeometry';
import { useLight } from './useLight';
import { useSuggestions } from './useSuggestions';

/**
 * Everything about one open garden (doc 87).
 *
 * Lives in a workspace keyed by the garden's token, so opening another garden
 * starts every piece of this from nothing: the selection, the filters, the armed
 * tool, the day being watched, the undo stack. Before the split, going home reset
 * eight of thirty-six pieces of state and opening a garden reset none.
 */
export function useGarden(
  client: NinaNaturClient,
  garden: GardenOut,
  setGarden: (garden: GardenOut) => void,
  status: Status,
  /** What to say once everything about the garden has arrived. */
  greeting: string,
) {
  const { remember, undo, depth } = useUndoStack();
  const derived = useDerived(client, garden, setGarden, status, greeting);
  const elements = useElements(client, garden, setGarden, status, derived.refresh, remember);
  const suggestions = useSuggestions(
    client,
    garden,
    setGarden,
    status,
    derived,
    elements.setSelectedObstacleId,
  );
  const clipboard = useClipboard(client, garden, setGarden, status, derived.refresh, suggestions);
  const geometry = useGeometry(client, garden, setGarden, status, remember);
  const light = useLight(
    client,
    garden.share_token,
    status,
    derived.setLightMap,
    suggestions.filters.floweringMonth ?? null,
  );

  const { run, setStatus } = status;
  const undoLast = useCallback(() => {
    void run('Rückgängig', async () => {
      const entry = await undo();
      setStatus(entry === null ? 'Nichts mehr zurückzunehmen.' : `${entry.label} zurückgenommen.`);
    });
  }, [run, setStatus, undo]);
  useUndoShortcut(undoLast, true);

  const { selectBed } = suggestions;
  const { setSelectedObstacleId, editObstacleById, setAsking } = elements;

  /** One selection, whichever way it was reached — the plan and the list
   *  disagreeing about what is selected is the obvious way for two views onto
   *  the same thing to go wrong (doc 52). */
  const selectElement = useCallback(
    (id: number) => {
      if (garden.beds.some((b) => b.bed_id === id)) {
        selectBed(id);
        setSelectedObstacleId(null);
      } else {
        editObstacleById(id);
      }
    },
    [garden, selectBed, setSelectedObstacleId, editObstacleById],
  );

  /** Escape drops whatever is selected, and the question the menu was asking. */
  const clearSelection = useCallback(() => {
    setSelectedObstacleId(null);
    setAsking(null);
  }, [setSelectedObstacleId, setAsking]);

  return {
    derived,
    elements,
    suggestions,
    clipboard,
    geometry,
    light,
    undo: undoLast,
    undoDepth: depth,
    selectElement,
    clearSelection,
  };
}

export type GardenController = ReturnType<typeof useGarden>;
