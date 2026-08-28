import { useCallback, useEffect, useState } from 'react';

import type { GardenOut } from './api/client';
import { NinaNaturClient } from './api/client';
import { BedPanel } from './components/BedPanel';
import { GardenCanvas } from './components/GardenCanvas';
import { NewGardenForm } from './components/NewGardenForm';

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

  const load = useCallback(async (token: string) => {
    const found = await client.getGarden(token);
    if (found === null) {
      setStatus('Dieser Link gehört zu keinem Garten (mehr).');
      return;
    }
    setGarden(found);
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
        setStatus(`Beet ${bed.name} hinzugefügt.`);
      });
    },
    [garden, run],
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
        <span className="badge">Wave&nbsp;3</span>
      </header>

      <main id="main" className="layout">
        {garden === null ? (
          <NewGardenForm onCreate={createGarden} busy={busy} />
        ) : (
          <>
            <BedPanel
              garden={garden}
              selectedBedId={selectedBedId}
              onSelectBed={setSelectedBedId}
              onAddBed={addBed}
              onAddObstacle={addObstacle}
              busy={busy}
            />
            <GardenCanvas
              garden={garden}
              selectedBedId={selectedBedId}
              onSelectBed={setSelectedBedId}
            />
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
