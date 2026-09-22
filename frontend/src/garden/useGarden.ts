import { useCallback, useEffect, useState } from 'react';

import type { GardenOut, NinaNaturClient } from '../api/client';
import { useUndoShortcut, useUndoStack } from '../useUndoStack';
import type { Status } from '../useStatus';
import { useClipboard } from './useClipboard';
import { useComputeShade } from './useComputeShade';
import { useDerived } from './useDerived';
import { useElements } from './useElements';
import { useGeometry } from './useGeometry';
import { useLight } from './useLight';
import { useSelection } from './useSelection';
import { useSuggestions } from './useSuggestions';

/**
 * Everything about one open garden (docs 87, 88, 89).
 *
 * Lives in a workspace keyed by the garden's token, so opening another garden
 * starts every piece of this from nothing: the selection, the filters, the armed
 * tool, the day being watched, the undo stack. Before the split, going home reset
 * eight of thirty-six pieces of state and opening a garden reset none.
 *
 * The selection comes first, and the rest are handed it: the plan, the element
 * list and the details read one selection, and no hook keeps its own piece.
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
  const chosen = useSelection(garden);
  const { selection, ids, clear } = chosen;
  const derived = useDerived(client, garden, setGarden, status, greeting);
  const elements = useElements(client, garden, setGarden, status, derived.refresh, remember, chosen);
  const suggestions = useSuggestions(client, garden, setGarden, status, derived, ids.bedId);
  const clipboard = useClipboard(
    client,
    garden,
    setGarden,
    status,
    derived.refresh,
    suggestions,
    selection,
  );
  const geometry = useGeometry(client, garden, setGarden, status, remember);
  // The shade switch stands in the garden's details, which show while nothing
  // is selected: selecting something hides the day's play button, and stops it.
  const light = useLight(
    client, garden.share_token, status, derived.setLightMap, selection.kind === 'none', setGarden,
  );

  const computeShade = useComputeShade(light.rebuilt, light.rebuild, suggestions.afterShade);
  // A rebuild is where a garden made before doc 114 first gets its surroundings.
  const { reloadLandcover } = derived;
  useEffect(() => {
    if (light.rebuilt > 0) reloadLandcover();
  }, [light.rebuilt, reloadLandcover]);

  const { run, setStatus } = status;
  const undoLast = useCallback(() => {
    void run('Rückgängig', async () => {
      const entry = await undo();
      setStatus(entry === null ? 'Nichts mehr zurückzunehmen.' : `${entry.label} zurückgenommen.`);
    });
  }, [run, setStatus, undo]);
  useUndoShortcut(undoLast, true);

  /** The species article, through the workspace's client rather than a
   *  module-level one (doc 88). Stable, because SpeciesInfo's effect depends on it. */
  const speciesInfo = useCallback((taxonId: number) => client.speciesInfo(taxonId), [client]);

  /** The plan's "N gefundene Bäume" (doc 89): back to the garden's details, where
   *  the card takes the focus once it is showing. */
  const [treesAsked, setTreesAsked] = useState(false);
  const showFoundTrees = useCallback(() => {
    clear();
    setTreesAsked(true);
  }, [clear]);
  const treesShown = useCallback(() => setTreesAsked(false), []);

  return {
    derived,
    elements,
    suggestions,
    clipboard,
    geometry,
    light,
    selection,
    ids,
    selectElement: chosen.selectElement,
    selectPlanting: chosen.selectPlanting,
    /** Escape, and every way back to the garden: nothing selected. */
    clearSelection: clear,
    askAbout: chosen.askAbout,
    askedFor: chosen.askedFor,
    focusTaken: chosen.focusTaken,
    speciesInfo,
    computeShade,
    showFoundTrees,
    treesAsked,
    treesShown,
    undo: undoLast,
    undoDepth: depth,
  };
}

export type GardenController = ReturnType<typeof useGarden>;
