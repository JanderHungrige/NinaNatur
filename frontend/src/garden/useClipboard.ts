import { useCallback, useEffect, useState } from 'react';

import type { BedSuggestions, GardenOut, NinaNaturClient, SuggestionFilters } from '../api/client';
import type { Status } from '../useStatus';

/** What Ctrl+C put aside: a species and how many of it, not a row id. */
interface Copied {
  taxonId: number | null;
  rawName: string | null;
  quantity: number;
  name: string;
}

interface FromSuggestions {
  selectedBedId: number | null;
  filters: SuggestionFilters;
  setSuggestions: (suggestions: BedSuggestions) => void;
}

/**
 * Patches of plants on the plan: which one is selected, dragging it, and copying
 * it into another bed (doc 87).
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
) {
  const { run, setStatus } = status;
  const { selectedBedId, filters, setSuggestions } = from;
  const token = garden.share_token;
  /** Which patch is selected. Separate from the bed and the shape: three things
   *  can be picked on this plan and they are not the same question. */
  const [selectedPlantingId, setSelectedPlantingId] = useState<number | null>(null);
  const [copied, setCopied] = useState<Copied | null>(null);

  const copyCluster = useCallback(() => {
    if (selectedPlantingId === null) return;
    for (const bed of garden.beds) {
      const found = bed.plantings.find((p) => p.planting_id === selectedPlantingId);
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
  }, [garden, selectedPlantingId, setStatus]);

  const pasteCluster = useCallback(() => {
    if (copied === null) return;
    if (selectedBedId === null) {
      setStatus('Wähle erst ein Beet, in das gepflanzt werden soll.');
      return;
    }
    const target = selectedBedId;
    void run('Einfügen', async () => {
      // Into the same bed it raises the count rather than starting a second
      // patch a metre away: one row per species per bed.
      const updated =
        copied.taxonId !== null
          ? await client.plant(token, target, copied.taxonId, copied.quantity)
          : await client.plantByName(token, target, {
              raw_name: copied.rawName ?? copied.name,
              quantity: copied.quantity,
            });
      setGarden(updated);
      await refresh();
      setSuggestions(await client.bedSuggestions(token, target, filters));
      setStatus(`${copied.name} eingefügt.`);
    });
  }, [client, token, copied, selectedBedId, filters, run, setGarden, refresh, setSuggestions, setStatus]);

  // Ctrl+C and Ctrl+V on the plan. Not while typing: a name being written in a
  // label field is what those keys mean there.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey)) return;
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
      ) {
        return;
      }
      const key = event.key.toLowerCase();
      if (key === 'c' && selectedPlantingId !== null) {
        event.preventDefault();
        copyCluster();
      } else if (key === 'v' && copied !== null) {
        event.preventDefault();
        pasteCluster();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selectedPlantingId, copied, copyCluster, pasteCluster]);

  const moveCluster = useCallback(
    (plantingId: number, to: { x: number; y: number }) => {
      void run('Verschieben', async () => {
        setGarden(await client.placePlanting(token, plantingId, to));
      });
    },
    [client, token, run, setGarden],
  );

  return { selectedPlantingId, setSelectedPlantingId, moveCluster };
}
