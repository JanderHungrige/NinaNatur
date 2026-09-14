import { useCallback, useMemo, useState } from 'react';

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

/** The species panel's subject: what the catalogue says, and what this garden noted. */
export interface InfoFor {
  taxonId: number;
  name: string;
  /** What the catalogue says, if anything. */
  recorded: string | null;
  /** What this garden noted, if anything. */
  noted: string | null;
}

interface FromDerived {
  refresh: () => Promise<void>;
  setImprovements: (value: ImprovementsOut) => void;
  palette: BloomPalette | null;
}

/**
 * The loop the workspace exists for: choose a bed, see what fits, plant it
 * (doc 87). Also the one selected month, and the species panel.
 */
export function useSuggestions(
  client: NinaNaturClient,
  garden: GardenOut,
  setGarden: (garden: GardenOut) => void,
  status: Status,
  derived: FromDerived,
  setSelectedObstacleId: (id: number | null) => void,
) {
  const { run, setStatus } = status;
  const { refresh, setImprovements, palette } = derived;
  const token = garden.share_token;
  const [selectedBedId, setSelectedBedId] = useState<number | null>(null);
  const [suggestions, setSuggestions] = useState<BedSuggestions | null>(null);
  const [filters, setFilters] = useState<SuggestionFilters>({});
  const [infoFor, setInfoFor] = useState<InfoFor | null>(null);

  /** Selecting a bed fetches its suggestions — the bed's own conditions are the query. */
  const selectBed = useCallback(
    (bedId: number) => {
      setSelectedBedId(bedId);
      // And as a shape, so the handles appear. Clicking a bed used to set only
      // the planting selection, which is half of why a bed could not be reshaped.
      setSelectedObstacleId(bedId);
      void run('Vorschläge laden', async () => {
        await Promise.all([
          client.bedSuggestions(token, bedId, filters).then(setSuggestions),
          client.improvements(token).then(setImprovements),
        ]);
      });
    },
    [client, token, filters, run, setSelectedObstacleId, setImprovements],
  );

  /** Refetch when the filters change — an explicit call rather than an effect
   *  keyed on `filters`, which cost this project one runaway request loop. */
  const changeFilters = useCallback(
    (next: SuggestionFilters) => {
      setFilters(next);
      if (selectedBedId === null) return;
      void run('Vorschläge laden', async () => {
        setSuggestions(await client.bedSuggestions(token, selectedBedId, next));
      });
    },
    [client, token, selectedBedId, run],
  );

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
      if (selectedBedId === null) return;
      const bedId = selectedBedId;
      await run('Pflanzen', async () => {
        // Re-read from the server: the timeline depends on data only it has.
        setGarden(await client.plant(token, bedId, taxonId));
        await Promise.all([
          refresh(),
          client.bedSuggestions(token, bedId, filters).then(setSuggestions),
        ]);
        setStatus(`${name} gepflanzt.`);
      });
    },
    [client, token, selectedBedId, filters, run, setGarden, refresh, setStatus],
  );

  const applyChange = useCallback(
    async (change: ChangeOut) => {
      await run('Pflanzen', async () => {
        setGarden(await client.plant(token, change.bed_id, change.taxon_id));
        await refresh();
        setStatus(`${change.canonical_name} gepflanzt — ${change.reason}.`);
      });
    },
    [client, token, run, setGarden, refresh, setStatus],
  );

  const addExisting = useCallback(
    (planting: { raw_name: string; quantity: number }) => {
      if (selectedBedId === null) return;
      const bedId = selectedBedId;
      void run('Eintragen', async () => {
        const updated = await client.plantByName(token, bedId, planting);
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
    [client, token, selectedBedId, run, setGarden, refresh, setStatus],
  );

  const removePlanting = useCallback(
    (plantingId: number) => {
      void run('Pflanze entfernen', async () => {
        setGarden(await client.removePlanting(token, plantingId));
        // The bloom year, the insect score and the palette all counted it.
        await refresh();
        if (selectedBedId !== null) {
          setSuggestions(await client.bedSuggestions(token, selectedBedId, filters));
        }
      });
    },
    [client, token, selectedBedId, filters, run, setGarden, refresh],
  );

  const showInfo = useCallback(
    (taxonId: number, name: string, recorded: string | null) =>
      setInfoFor({ taxonId, name, recorded, noted: garden.observed_colours[taxonId] ?? null }),
    [garden],
  );

  const closeInfo = useCallback(() => setInfoFor(null), []);

  const noteColour = useCallback(
    // Null takes a noted colour back: the catalogue's answer, or "unknown", again.
    (colour: string | null) => {
      const asked = infoFor;
      if (asked === null) return;
      void run('Blütenfarbe merken', async () => {
        setGarden(await client.noteColour(token, asked.taxonId, colour));
        await refresh();
        // The list is where the colour was missing from, and `refresh` does not
        // re-read it: without this the row still said "Farbe unbekannt".
        if (selectedBedId !== null) {
          setSuggestions(await client.bedSuggestions(token, selectedBedId, filters));
        }
        // Only once it is stored. Setting it first showed "von dir eingetragen"
        // over a 405 for a route mounted at the wrong path.
        setInfoFor({ ...asked, noted: colour });
      });
    },
    [client, token, infoFor, selectedBedId, filters, run, setGarden, refresh],
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
    selectedBedId,
    selectBed,
    suggestions,
    setSuggestions,
    filters,
    changeFilters,
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
  };
}

export type Suggestions = ReturnType<typeof useSuggestions>;
