import { useCallback, useEffect, useState } from 'react';

import type {
  BedSuggestions,
  ChangeOut,
  GardenOut,
  SuggestionFilters,
  ImprovementsOut,
  ScoreOut,
  TimelineOut,
} from './api/client';
import { NinaNaturClient } from './api/client';
import { BedPanel } from './components/BedPanel';
import { BloomTimeline } from './components/BloomTimeline';
import { GardenCanvas } from './components/GardenCanvas';
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
              <FilterControls filters={filters} onChange={changeFilters} disabled={busy} />
              <FilterBar
                filters={filters}
                counts={suggestions?.filters ?? {}}
                onChange={changeFilters}
              />
              <SuggestionList
                includeTrees={filters.includeTrees === true}
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
              />
              {timeline !== null ? (
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
