import { useCallback, useEffect, useState } from 'react';

import type { BedSuggestions, GardenOut, TimelineOut } from './api/client';
import { NinaNaturClient } from './api/client';
import { BedPanel } from './components/BedPanel';
import { BloomTimeline } from './components/BloomTimeline';
import { GardenCanvas } from './components/GardenCanvas';
import { NewGardenForm } from './components/NewGardenForm';
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

  const load = useCallback(async (token: string, weighted = true) => {
    const found = await client.getGarden(token);
    if (found === null) {
      setStatus('Dieser Link gehört zu keinem Garten (mehr).');
      return;
    }
    setGarden(found);
    setTimeline(await client.timeline(token, weighted));
    setStatus(`${found.name} geladen.`);
  }, []);

  useEffect(() => {
    const token = tokenFromHash();
    if (token !== null) {
      void load(token);
    }
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
        setSuggestions(await client.bedSuggestions(garden.share_token, bedId));
      });
    },
    [garden, run],
  );

  const plant = useCallback(
    async (taxonId: number, name: string) => {
      if (garden === null || selectedBedId === null) return;
      await run('Pflanzen', async () => {
        // Re-read from the server: the timeline depends on data only it has.
        const updated = await client.plant(garden.share_token, selectedBedId, taxonId);
        setGarden(updated);
        setTimeline(await client.timeline(garden.share_token, forage));
        setSuggestions(await client.bedSuggestions(garden.share_token, selectedBedId));
        setStatus(`${name} gepflanzt.`);
      });
    },
    [garden, selectedBedId, forage, run],
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
        setTimeline(await client.timeline(garden.share_token, forage));
        setStatus(`Beet ${bed.name} hinzugefügt.`);
      });
    },
    [garden, forage, run],
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
        <span className="badge">Wave&nbsp;4</span>
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
              <SuggestionList suggestions={suggestions} onPlant={plant} busy={busy} />
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
