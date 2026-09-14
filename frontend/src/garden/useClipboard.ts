import { useCallback, useEffect, useState } from 'react';

import type { BedSuggestions, GardenOut, NinaNaturClient, SuggestionFilters } from '../api/client';
import type { Status } from '../useStatus';
import type { Selection } from './selection';

/** What Ctrl+C put aside: a species and how many of it, not a row id. */
interface Copied {
  taxonId: number | null;
  rawName: string | null;
  quantity: number;
  name: string;
}

interface FromSuggestions {
  filters: SuggestionFilters;
  setSuggestions: (suggestions: BedSuggestions) => void;
}

/**
 * Patches of plants on the plan: dragging one, and copying it into another bed
 * (docs 87, 88). Which patch is selected is the selection's.
 *
 * The clipboard holds a species and a count: pasting is planting the same thing
 * again, and a row id would be a reference to somebody else's row.
 */
export function useClipboard(
  client: NinaNaturClient,
  garden: GardenOut,
  setGarden: (garden: GardenOut) => void,
  status: Status,
  refresh: () => Promise<void>,
  from: FromSuggestions,
  selection: Selection,
) {
  const { run, setStatus } = status;
  const { filters, setSuggestions } = from;
  const token = garden.share_token;
  const [copied, setCopied] = useState<Copied | null>(null);
  const plantingId = selection.kind === 'planting' ? selection.planting.planting_id : null;
  /** Where a paste goes: the selected bed, or the bed of the selected patch. */
  const target =
    selection.kind === 'bed' || selection.kind === 'planting' ? selection.bed.bed_id : null;

  const copyCluster = useCallback(() => {
    if (plantingId === null) return;
    for (const bed of garden.beds) {
      const found = bed.plantings.find((p) => p.planting_id === plantingId);
      if (found === undefined) continue;
      setCopied({
        taxonId: found.taxon_id,
        rawName: found.raw_name,
        quantity: found.quantity,
        name: found.canonical_name ?? found.raw_name ?? 'Pflanzung',
      });
      setStatus(`${found.canonical_name ?? found.raw_name} kopiert.`);
      return;
    }
  }, [garden, plantingId, setStatus]);

  const pasteCluster = useCallback(() => {
    if (copied === null) return;
    if (target === null) {
      setStatus('Wähle erst ein Beet, in das gepflanzt werden soll.');
      return;
    }
    const into = target;
    void run('Einfügen', async () => {
      // Into the same bed it raises the count rather than starting a second
      // patch a metre away: one row per species per bed.
      const updated =
        copied.taxonId !== null
          ? await client.plant(token, into, copied.taxonId, copied.quantity)
          : await client.plantByName(token, into, {
              raw_name: copied.rawName ?? copied.name,
              quantity: copied.quantity,
            });
      setGarden(updated);
      await refresh();
      setSuggestions(await client.bedSuggestions(token, into, filters));
      setStatus(`${copied.name} eingefügt.`);
    });
  }, [client, token, copied, target, filters, run, setGarden, refresh, setSuggestions, setStatus]);

  // Ctrl+C and Ctrl+V on the plan. Not while typing: a name being written in a
  // label field is what those keys mean there.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey)) return;
      const eventTarget = event.target;
      if (
        eventTarget instanceof HTMLElement &&
        (eventTarget.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(eventTarget.tagName))
      ) {
        return;
      }
      const key = event.key.toLowerCase();
      if (key === 'c' && plantingId !== null) {
        event.preventDefault();
        copyCluster();
      } else if (key === 'v' && copied !== null) {
        event.preventDefault();
        pasteCluster();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [plantingId, copied, copyCluster, pasteCluster]);

  const moveCluster = useCallback(
    (movedId: number, to: { x: number; y: number }) => {
      void run('Verschieben', async () => {
        setGarden(await client.placePlanting(token, movedId, to));
      });
    },
    [client, token, run, setGarden],
  );

  return { moveCluster };
}
