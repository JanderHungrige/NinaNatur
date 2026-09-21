import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type {
  BedSuggestions,
  BloomPalette,
  ChangeOut,
  GardenOut,
  ImprovementsOut,
  NinaNaturClient,
  SuggestionFilters,
} from '../api/client';
import { clustersFor } from '../canvas/clusters';
import type { Status } from '../useStatus';

/** The species panel's subject. What this garden noted about it is read from the
 *  garden when the panel is shown, so it only ever says what the server stored. */
export interface InfoFor {
  taxonId: number;
  name: string;
  /** What the catalogue says, if anything. */
  recorded: string | null;
}

interface FromDerived {
  refresh: () => Promise<void>;
  setImprovements: (value: ImprovementsOut) => void;
  palette: BloomPalette | null;
}

/** How long a patch that was just planted stays marked on the plan (doc 88). */
export const FRESH_MS = 2400;

/** The patch a planting went into: that species' row in that bed, new or grown. */
function patchOf(garden: GardenOut, bedId: number, taxonId: number): number | null {
  const bed = garden.beds.find((b) => b.bed_id === bedId);
  return bed?.plantings.find((p) => p.taxon_id === taxonId)?.planting_id ?? null;
}

/**
 * The loop the workspace exists for: a bed, what fits it, planting it (docs 87,
 * 88). Also the one selected month, and the species panel. Which bed is selected
 * is the selection's; this hook is told.
 */
export function useSuggestions(
  client: NinaNaturClient,
  garden: GardenOut,
  setGarden: (garden: GardenOut) => void,
  status: Status,
  derived: FromDerived,
  /** The bed selected for planting, when a bed is selected. */
  bedId: number | null,
) {
  const { run, setStatus } = status;
  const { refresh, setImprovements, palette } = derived;
  const token = garden.share_token;
  const [suggestions, setSuggestions] = useState<BedSuggestions | null>(null);
  /** A bed whose suggestions could not be loaded, so its view can say so. */
  const [failedFor, setFailedFor] = useState<number | null>(null);
  const [filters, setFilters] = useState<SuggestionFilters>({});
  const [infoFor, setInfoFor] = useState<InfoFor | null>(null);
  const [freshPlantingId, setFreshPlantingId] = useState<number | null>(null);

  // The filters as they are, for the effect below: read by it, never a reason
  // for it to run.
  const filtersNow = useRef(filters);
  useEffect(() => {
    filtersNow.current = filters;
  }, [filters]);

  /**
   * The suggestions follow the selected bed, however it came to be selected: on
   * the plan, in a list, or by an element being called Blumenbeet (doc 88).
   *
   * Keyed on the bed's id alone. An effect keyed on the filters is the runaway
   * request loop this project has already paid for once, and `changeFilters`
   * refetches explicitly.
   */
  useEffect(() => {
    if (bedId === null) return undefined;
    let current = true;
    setFailedFor(null);
    setInfoFor(null);
    void run('Vorschläge laden', async () => {
      try {
        const [found, better] = await Promise.all([
          client.bedSuggestions(token, bedId, filtersNow.current),
          client.improvements(token),
        ]);
        if (!current) return;
        setSuggestions(found);
        setImprovements(better);
      } catch (error) {
        if (current) setFailedFor(bedId);
        throw error;
      }
    });
    return () => {
      current = false;
    };
  }, [client, token, bedId, run, setImprovements]);

  // A mark, not a state: it fades on its own.
  useEffect(() => {
    if (freshPlantingId === null) return undefined;
    const timer = window.setTimeout(() => setFreshPlantingId(null), FRESH_MS);
    return () => window.clearTimeout(timer);
  }, [freshPlantingId]);

  /** Refetch when the filters change — an explicit call rather than an effect
   *  keyed on `filters`, which cost this project one runaway request loop. */
  const changeFilters = useCallback(
    (next: SuggestionFilters) => {
      setFilters(next);
      if (bedId === null) return;
      void run('Vorschläge laden', async () => {
        setSuggestions(await client.bedSuggestions(token, bedId, next));
      });
    },
    [client, token, bedId, run],
  );

  /** Re-read the list, and the garden it was ranked from, once the shade has
   *  been computed: the bed's light value and `light_state` both change, and
   *  the bed's own line would otherwise go on saying "noch nicht berechnet". */
  const afterShade = useCallback(() => {
    if (bedId === null) return;
    const target = bedId;
    void run('Vorschläge laden', async () => {
      const [found, updated] = await Promise.all([
        client.bedSuggestions(token, target, filtersNow.current),
        client.getGarden(token),
      ]);
      setSuggestions(found);
      if (updated !== null) setGarden(updated);
    });
  }, [client, token, bedId, run, setGarden]);

  /** One selected month, two ways in (doc 24): the player steps to one, the
   *  timeline toggles one, and null clears it. */
  const selectMonth = useCallback(
    (month: number | null) =>
      changeFilters(
        month === null
          ? (({ floweringMonth: _drop, ...rest }) => rest)(filters)
          : { ...filters, floweringMonth: month },
      ),
    [changeFilters, filters],
  );

  const plant = useCallback(
    async (taxonId: number, name: string) => {
      if (bedId === null) return;
      const target = bedId;
      await run('Pflanzen', async () => {
        // Re-read from the server: the timeline depends on data only it has.
        const updated = await client.plant(token, target, taxonId);
        setGarden(updated);
        // The plan shows where it went; the details stay where they are (doc 88).
        setFreshPlantingId(patchOf(updated, target, taxonId));
        await Promise.all([
          refresh(),
          client.bedSuggestions(token, target, filters).then(setSuggestions),
        ]);
        setStatus(`${name} gepflanzt.`);
      });
    },
    [client, token, bedId, filters, run, setGarden, refresh, setStatus],
  );

  const applyChange = useCallback(
    async (change: ChangeOut) => {
      await run('Pflanzen', async () => {
        const updated = await client.plant(token, change.bed_id, change.taxon_id);
        setGarden(updated);
        setFreshPlantingId(patchOf(updated, change.bed_id, change.taxon_id));
        await refresh();
        setStatus(`${change.canonical_name} gepflanzt — ${change.reason}.`);
      });
    },
    [client, token, run, setGarden, refresh, setStatus],
  );

  const addExisting = useCallback(
    (planting: { raw_name: string; quantity: number }) => {
      if (bedId === null) return;
      const target = bedId;
      void run('Eintragen', async () => {
        const updated = await client.plantByName(token, target, planting);
        setGarden(updated);
        await refresh();
        const added = updated.beds
          .flatMap((b) => b.plantings)
          .find((p) => p.raw_name === planting.raw_name);
        setStatus(
          added?.canonical_name != null
            ? `${planting.raw_name} als ${added.canonical_name} eingetragen.`
            : `${planting.raw_name} eingetragen — noch keiner Art zugeordnet.`,
        );
      });
    },
    [client, token, bedId, run, setGarden, refresh, setStatus],
  );

  const removePlanting = useCallback(
    (plantingId: number) => {
      void run('Pflanze entfernen', async () => {
        setGarden(await client.removePlanting(token, plantingId));
        // The bloom year, the insect score and the palette all counted it.
        await refresh();
        if (bedId !== null) {
          setSuggestions(await client.bedSuggestions(token, bedId, filters));
        }
      });
    },
    [client, token, bedId, filters, run, setGarden, refresh],
  );

  const showInfo = useCallback(
    (taxonId: number, name: string, recorded: string | null) =>
      setInfoFor({ taxonId, name, recorded }),
    [],
  );

  const closeInfo = useCallback(() => setInfoFor(null), []);

  /** A colour noted from the photograph, for one species. Null takes it back: the
   *  catalogue's answer, or "unknown", again. */
  const noteColour = useCallback(
    (taxonId: number, colour: string | null) => {
      void run('Blütenfarbe merken', async () => {
        // The panel reads what was noted from this answer, so it says "von dir
        // eingetragen" only once the server has stored it — not over a 405.
        setGarden(await client.noteColour(token, taxonId, colour));
        await refresh();
        // The list is where the colour was missing from, and `refresh` does not
        // re-read it: without this the row still said "Farbe unbekannt".
        if (bedId !== null) {
          setSuggestions(await client.bedSuggestions(token, bedId, filters));
        }
      });
    },
    [client, token, bedId, filters, run, setGarden, refresh],
  );

  /** Every planting as a patch ready to draw, in the selected month's colours —
   *  grey when no month is selected, the honest reading outside the bloom year. */
  const clusters = useMemo(() => {
    const byBed = new Map((palette?.beds ?? []).map((b) => [b.bed_id, b.plantings]));
    return garden.beds.flatMap((bed) =>
      clustersFor(bed.polygon, bed.plantings, byBed.get(bed.bed_id) ?? [], filters.floweringMonth ?? null),
    );
  }, [garden, palette, filters.floweringMonth]);

  return {
    suggestions,
    setSuggestions,
    failedFor,
    filters,
    changeFilters,
    afterShade,
    selectMonth,
    plant,
    applyChange,
    addExisting,
    removePlanting,
    infoFor,
    showInfo,
    closeInfo,
    noteColour,
    clusters,
    freshPlantingId,
  };
}

export type Suggestions = ReturnType<typeof useSuggestions>;
