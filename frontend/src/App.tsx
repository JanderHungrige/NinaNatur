import { useCallback, useEffect, useState } from 'react';

import type {
  BedSuggestions,
  ChangeOut,
  BloomPalette,
  GardenOut,
  SuggestionFilters,
  ImprovementsOut,
  ScoreOut,
  TimelineOut,
} from './api/client';
import { NinaNaturClient } from './api/client';
import { BedPanel } from './components/BedPanel';
import { BloomPlayer } from './components/BloomPlayer';
import { BloomTimeline } from './components/BloomTimeline';
import { GardenCanvas } from './components/GardenCanvas';
import { ExistingPlanting } from './components/ExistingPlanting';
import { ObjectEditor, type EditableObject } from './components/ObjectEditor';
import { InsectScore } from './components/InsectScore';
import { NewGardenForm } from './components/NewGardenForm';
import { SpeciesInfo } from './components/SpeciesInfo';
import { FilterBar } from './components/FilterBar';
import { FilterControls } from './components/FilterControls';
import { SuggestionList } from './components/SuggestionList';

const client = new NinaNaturClient();

/**
 * The share token lives in the URL fragment, not the path or query. A fragment is
 * never sent to a server, so it cannot leak through a Referer header when the
 * user follows a link out of the app.
 */
function tokenFromHash(): string | null {
  const hash = window.location.hash.replace(/^#/, '');
  return hash.length > 0 ? hash : null;
}

export function App() {
  const [garden, setGarden] = useState<GardenOut | null>(null);
  const [selectedBedId, setSelectedBedId] = useState<number | null>(null);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [timeline, setTimeline] = useState<TimelineOut | null>(null);
  const [suggestions, setSuggestions] = useState<BedSuggestions | null>(null);
  const [forage, setForage] = useState(true);
  const [score, setScore] = useState<ScoreOut | null>(null);
  const [version, setVersion] = useState<string | null>(null);
  const [infoFor, setInfoFor] = useState<{ taxonId: number; name: string } | null>(null);
  const [improvements, setImprovements] = useState<ImprovementsOut | null>(null);
  const [filters, setFilters] = useState<SuggestionFilters>({});
  const [editing, setEditing] = useState<EditableObject | null>(null);
  const [palette, setPalette] = useState<BloomPalette | null>(null);

  const load = useCallback(async (token: string, weighted = true) => {
    const found = await client.getGarden(token);
    if (found === null) {
      setStatus('Dieser Link gehört zu keinem Garten (mehr).');
      return;
    }
    setGarden(found);
    setTimeline(await client.timeline(token, weighted));
    setScore(await client.score(token));
    // Loaded here rather than on bed selection: the suggestions are the point of
    // the score, and hiding them until something is clicked buries it.
    setImprovements(await client.improvements(token));
    // Also here, not only in refresh: a garden opened from its link never goes
    // through refresh, so the plan had no colours until something was edited.
    setPalette(await client.bloom(token));
    setStatus(`${found.name} geladen.`);
  }, []);

  useEffect(() => {
    const token = tokenFromHash();
    if (token !== null) {
      void load(token);
    }
    // A failed version lookup must not stop the app from loading — it is a label.
    void client.version().then(setVersion).catch(() => setVersion(null));
  }, [load]);

  /** Wrap every mutation so a failed request always reaches the live region. */
  const run = useCallback(async (label: string, action: () => Promise<void>) => {
    setBusy(true);
    try {
      await action();
    } catch (error) {
      setStatus(`${label} fehlgeschlagen: ${(error as Error).message}`);
    } finally {
      setBusy(false);
    }
  }, []);

  /** Selecting a bed fetches its suggestions — the bed's own conditions are the query. */
  const selectBed = useCallback(
    (bedId: number) => {
      setSelectedBedId(bedId);
      if (garden === null) return;
      void run('Vorschläge laden', async () => {
        setSuggestions(await client.bedSuggestions(garden.share_token, bedId, filters));
        setImprovements(await client.improvements(garden.share_token));
      });
    },
    [garden, filters, run],
  );

  /**
   * Refetch when the filters change.
   *
   * Done here rather than in an effect keyed on `filters`: the suggestion panel
   * already cost this project one runaway request loop from an effect whose
   * dependency was recreated on every render. An explicit call happens exactly
   * when the user changes something.
   */
  const changeFilters = useCallback(
    (next: SuggestionFilters) => {
      setFilters(next);
      if (garden === null || selectedBedId === null) return;
      void run('Vorschläge laden', async () => {
        setSuggestions(await client.bedSuggestions(garden.share_token, selectedBedId, next));
      });
    },
    [garden, selectedBedId, run],
  );

  /** Everything the server derives, re-read together after any change. */
  const refresh = useCallback(async (token: string, weighted: boolean) => {
    setTimeline(await client.timeline(token, weighted));
    setScore(await client.score(token));
    setImprovements(await client.improvements(token));
    setPalette(await client.bloom(token));
  }, []);

  const applyChange = useCallback(
    async (change: ChangeOut) => {
      if (garden === null) return;
      await run('Pflanzen', async () => {
        const updated = await client.plant(garden.share_token, change.bed_id, change.taxon_id);
        setGarden(updated);
        await refresh(garden.share_token, forage);
        setStatus(`${change.canonical_name} gepflanzt — ${change.reason}.`);
      });
    },
    [garden, forage, refresh, run],
  );

  const plant = useCallback(
    async (taxonId: number, name: string) => {
      if (garden === null || selectedBedId === null) return;
      await run('Pflanzen', async () => {
        // Re-read from the server: the timeline depends on data only it has.
        const updated = await client.plant(garden.share_token, selectedBedId, taxonId);
        setGarden(updated);
        await refresh(garden.share_token, forage);
        setSuggestions(await client.bedSuggestions(garden.share_token, selectedBedId, filters));
        setStatus(`${name} gepflanzt.`);
      });
    },
    [garden, selectedBedId, forage, filters, refresh, run],
  );

  const toggleForage = useCallback(
    (weighted: boolean) => {
      setForage(weighted);
      if (garden === null) return;
      void run('Gewichtung wechseln', async () => {
        const next = await client.timeline(garden.share_token, weighted);
        setTimeline(next);
        setStatus(
          next.gaps.length === 0
            ? 'Keine Lücke zwischen März und Oktober.'
            : `${next.gaps.length} Lücke(n) in dieser Ansicht.`,
        );
      });
    },
    [garden, run],
  );

  const createGarden = useCallback(
    async (input: { name: string; latitude: number; longitude: number }) => {
      await run('Anlegen', async () => {
        const created = await client.createGarden(input);
        window.location.hash = created.share_token;
        await load(created.share_token);
      });
    },
    [load, run],
  );

  const addBed = useCallback(
    async (bed: { name: string; polygon: number[][]; soil_type: string; moisture: string }) => {
      if (garden === null) return;
      await run('Beet hinzufügen', async () => {
        // Re-render from the server's answer rather than local optimism: only the
        // server can compute light, and guessing it here would show a number the
        // data does not support.
        const updated = await client.addBed(garden.share_token, bed);
        setGarden(updated);
        await refresh(garden.share_token, forage);
        setStatus(`Beet ${bed.name} hinzugefügt.`);
      });
    },
    [garden, forage, refresh, run],
  );

  /**
   * A polygon drawn on the plan becomes a bed with a placeholder name and the
   * default soil, which the bed form then edits. Asking for a name mid-drawing
   * would interrupt the one gesture the whole feature exists for.
   */
  const drawBed = useCallback(
    (polygon: number[][]) => {
      const nth = (garden?.beds.length ?? 0) + 1;
      void addBed({
        name: `Beet ${nth}`,
        polygon,
        soil_type: 'loam',
        moisture: 'fresh',
      });
    },
    [garden, addBed],
  );

  /**
   * Saving an edit re-reads the garden from the server: raising a bed or
   * growing a hedge changes every bed's light, and only the server can say by
   * how much.
   */
  const saveObject = useCallback(
    (changes: Record<string, string | number>) => {
      if (garden === null || editing === null) return;
      const target = editing;
      void run('Speichern', async () => {
        const updated =
          target.kind === 'bed'
            ? await client.editBed(garden.share_token, target.id, changes)
            : await client.editObstacle(garden.share_token, target.id, changes);
        setGarden(updated);
        await refresh(garden.share_token, forage);
        setEditing(null);
      });
    },
    [garden, editing, forage, refresh, run],
  );

  const addExisting = useCallback(
    (planting: { raw_name: string; quantity: number }) => {
      if (garden === null || selectedBedId === null) return;
      void run('Eintragen', async () => {
        const updated = await client.plantByName(garden.share_token, selectedBedId, planting);
        setGarden(updated);
        await refresh(garden.share_token, forage);
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
    [garden, selectedBedId, forage, refresh, run],
  );

  /**
   * The colours to paint for the month currently selected.
   *
   * Keyed off the same `floweringMonth` the filter and the timeline use — one
   * selected month, not a separate playback one that could drift from it.
   */
  const monthColours =
    filters.floweringMonth === undefined || palette === null
      ? undefined
      : Object.fromEntries(
          palette.beds.map((b) => {
            const m = b.months.find((x) => x.month === filters.floweringMonth);
            return [b.bed_id, { colours: m?.colours ?? [], unknown: m?.unknown ?? 0 }];
          }),
        );

  const editSelectedBed = useCallback(() => {
    const bed = garden?.beds.find((b) => b.bed_id === selectedBedId);
    if (bed === undefined) return;
    setEditing({
      kind: 'bed',
      id: bed.bed_id,
      name: bed.name,
      label: bed.label,
      heightAboveGround: bed.height_above_ground,
    });
  }, [garden, selectedBedId]);

  const editObstacleById = useCallback(
    (obstacleId: number) => {
      const found = garden?.obstacles.find((o) => o.obstacle_id === obstacleId);
      if (found === undefined) return;
      setEditing({
        kind: 'obstacle',
        id: found.obstacle_id,
        objectKind: found.kind,
        label: found.label,
        height: found.height,
        radius: found.radius,
      });
    },
    [garden],
  );

  const addObstacle = useCallback(
    async (obstacle: { kind: string; x: number; y: number; radius: number; height: number }) => {
      if (garden === null) return;
      await run('Hindernis hinzufügen', async () => {
        const updated = await client.addObstacle(garden.share_token, obstacle);
        setGarden(updated);
        const lit = updated.beds
          .map((b) => (b.sun_hours === null ? '?' : b.sun_hours.toFixed(1)))
          .join(', ');
        setStatus(`Hindernis gesetzt. Sonnenstunden jetzt: ${lit}.`);
      });
    },
    [garden, run],
  );

  return (
    <>
      <a className="skip-link" href="#main">Zum Inhalt springen</a>
      <header className="site-header">
        <span className="brand">
          <span className="brand__name">NinaNatur</span>
        </span>
        {version !== null ? (
          <span className="badge" title="Version · Wave · Merges auf main">{version}</span>
        ) : null}
      </header>

      <main id="main" className="layout">
        {garden === null ? (
          <NewGardenForm onCreate={createGarden} busy={busy} />
        ) : (
          <>
            <div className="column">
              <BedPanel
                garden={garden}
                selectedBedId={selectedBedId}
                onSelectBed={selectBed}
                onAddBed={addBed}
                onAddObstacle={addObstacle}
                busy={busy}
              />
              {selectedBedId !== null ? (
                <ExistingPlanting
                  onAdd={addExisting}
                  unidentified={garden.unidentified_plantings}
                  busy={busy}
                />
              ) : null}
              {selectedBedId !== null && editing === null ? (
                <button type="button" className="link-button" onClick={editSelectedBed}>
                  Gewähltes Beet bearbeiten
                </button>
              ) : null}
              {editing !== null ? (
                <ObjectEditor
                  object={editing}
                  onSave={saveObject}
                  onClose={() => setEditing(null)}
                  busy={busy}
                />
              ) : null}
              <FilterControls filters={filters} onChange={changeFilters} disabled={busy} />
              <FilterBar
                filters={filters}
                counts={suggestions?.filters ?? {}}
                onChange={changeFilters}
              />
              <SuggestionList
                includeTrees={filters.includeTrees !== false}
                suggestions={suggestions}
                onPlant={plant}
                onShowInfo={(taxonId, name) => setInfoFor({ taxonId, name })}
                busy={busy}
              />
              {infoFor !== null ? (
                <SpeciesInfo
                  taxonId={infoFor.taxonId}
                  canonicalName={infoFor.name}
                  onClose={() => setInfoFor(null)}
                />
              ) : null}
            </div>
            <div className="column">
              <GardenCanvas
                garden={garden}
                selectedBedId={selectedBedId}
                onSelectBed={selectBed}
                onDrawBed={drawBed}
                onSelectObstacle={editObstacleById}
                palette={monthColours}
              />
              {timeline !== null ? (
                <>
                <BloomPlayer
                  month={filters.floweringMonth ?? null}
                  onSelectMonth={(m) => changeFilters({ ...filters, floweringMonth: m })}
                />
                <BloomTimeline
                  timeline={timeline}
                  forage={forage}
                  onToggleForage={toggleForage}
                  busy={busy}
                selectedMonth={filters.floweringMonth ?? null}
                onSelectMonth={(month) =>
                  changeFilters(
                    month === null
                      ? (({ floweringMonth: _drop, ...rest }) => rest)(filters)
                      : { ...filters, floweringMonth: month },
                  )
                }
              />
                </>
              ) : null}
              {score !== null ? (
                <InsectScore
                  score={score}
                  improvements={improvements}
                  onApply={applyChange}
                  busy={busy}
                />
              ) : null}
            </div>
          </>
        )}
      </main>

      {/* Status is announced, not only shown — a colour change is invisible to a
          screen reader and to anyone not looking at that part of the page. */}
      <p className="status" role="status" aria-live="polite">
        {status}
      </p>
    </>
  );
}
