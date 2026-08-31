import { useCallback, useEffect, useState } from 'react';

import type {
  BedSuggestions,
  ChangeOut,
  BloomPalette,
  GardenOut,
  SightlinesOut,
  SuggestionFilters,
  ImprovementsOut,
  ScoreOut,
  TimelineOut,
} from './api/client';
import { NinaNaturClient } from './api/client';
import { BedPanel } from './components/BedPanel';
import { AccountPanel, type AccountInfo } from './components/AccountPanel';
import { BloomPlayer } from './components/BloomPlayer';
import { BloomTimeline } from './components/BloomTimeline';
import { GardenCanvas } from './components/GardenCanvas';
import { ShapeTools } from './components/ShapeTools';
import { GardenId } from './components/GardenId';
import { objects } from './plural';
import { Landing } from './components/Landing';
import { MapPicker, type MapSelection } from './components/MapPicker';
import { Sightlines } from './components/Sightlines';
import { ExistingPlanting } from './components/ExistingPlanting';
import { type Box, boxOf } from './canvas/handles';
import type { DrawnShape, Tool } from './canvas/shapes';
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
  const [openProblem, setOpenProblem] = useState<string | undefined>(undefined);
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [sightlines, setSightlines] = useState<SightlinesOut | null>(null);
  const [viewpoint, setViewpoint] = useState<{ x: number; y: number } | null>(null);

  /** Stable identity: an inline arrow would refire the landing page's effect
   *  on every render, which is the loop the species panel already cost us. */
  const loadStats = useCallback(async () => client.stats(), []);


  const findPlaces = useCallback(async (q: string) => client.findPlaces(q), []);
  const findImagery = useCallback(
    async (lat: number, lon: number) => client.findImagery(lat, lon),
    [],
  );



  const load = useCallback(async (token: string, weighted = true) => {
    const found = await client.getGarden(token);
    if (found === null) {
      // Back to the front door with the field still filled: an unknown id must
      // not look like an empty garden.
      setOpenProblem('Zu dieser ID gibt es keinen Garten.');
      setStatus('');
      return;
    }
    setOpenProblem(undefined);
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

  // Who is logged in, asked once. Not being logged in is the ordinary state, so
  // the client answers null rather than throwing.
  useEffect(() => {
    void client.me().then(setAccount).catch(() => setAccount(null));
  }, []);

  const register = useCallback(
    async (input: { username: string; password: string; email?: string }) => {
      await run('Konto anlegen', async () => {
        await client.register(input);
        setAccount(await client.logIn({ username: input.username, password: input.password }));
        setStatus('Konto angelegt und angemeldet.');
      });
    },
    [run],
  );

  const logIn = useCallback(
    async (input: { username: string; password: string }) => {
      await run('Anmelden', async () => {
        setAccount(await client.logIn(input));
        setStatus('Angemeldet.');
      });
    },
    [run],
  );

  const logOut = useCallback(async () => {
    await run('Abmelden', async () => {
      await client.logOut();
      setAccount(null);
      setStatus('Abgemeldet. Deine Garten-ID öffnet den Garten weiterhin.');
    });
  }, [run]);

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

  /**
   * A garden made from a map selection arrives with its surroundings already
   * placed, so the status line says what the map could and could not tell us —
   * an assumed height presented as a measured one would be the same lie as a
   * filter that hides what it dropped.
   */
  const createFromMap = useCallback(
    (selection: MapSelection) => {
      void run('Anlegen', async () => {
        const result = await client.gardenFromMap(selection);
        window.location.hash = result.garden.share_token;
        await load(result.garden.share_token);
        const { measured, estimated, assumed } = result.heights;
        const placed = measured + estimated + assumed;
        setStatus(
          placed === 0
            ? 'Garten angelegt. In der Umgebung stand nichts, was Schatten wirft.'
            // Nominative, so the sentence needs no dative the plural helper
            // cannot give it: "mit 2 Objekte" is "1 Beete" one case further on.
            : `Garten angelegt. ${objects(placed)} aus der Karte übernommen — ` +
              `${measured} gemessen, ${estimated} aus Geschossen, ${assumed} angenommen.`,
        );
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

  /**
   * Standing somewhere and asking what is visible.
   *
   * Computed on the server because it needs plant heights from the catalogue,
   * which the browser does not have.
   */
  const lookFrom = useCallback(
    (x: number, y: number) => {
      if (garden === null) return;
      setViewpoint({ x, y });
      void run('Sichtprüfung', async () => {
        setSightlines(await client.sightlines(garden.share_token, { x, y }));
      });
    },
    [garden, run],
  );

  const claim = useCallback(() => {
    if (garden === null) return;
    void run('Übernehmen', async () => {
      setGarden(await client.claimGarden(garden.share_token));
      setStatus('Dieser Garten gehört jetzt zu deinem Konto.');
    });
  }, [garden, run]);

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

  /** The element the palette has armed. Null is the ordinary state: a plan the
   *  user can click without placing anything. */
  const [tool, setTool] = useState<Tool | null>(null);
  const [selectedObstacleId, setSelectedObstacleId] = useState<number | null>(null);

  const editObstacleById = useCallback(
    (obstacleId: number) => {
      const found = garden?.obstacles.find((o) => o.obstacle_id === obstacleId);
      if (found === undefined) return;
      setSelectedObstacleId(obstacleId);
      setEditing({
        kind: 'obstacle',
        id: found.obstacle_id,
        objectKind: found.kind,
        label: found.label,
        height: found.height,
        width: boxOf(found).width,
        depth: boxOf(found).depth,
      });
    },
    [garden],
  );

  const addObstacle = useCallback(
    async (obstacle: {
      kind: string;
      x: number;
      y: number;
      shape?: string;
      width?: number;
      depth?: number;
      points?: number[][];
      height?: number;
    }) => {
      if (garden === null) return;
      const before = new Set(garden.obstacles.map((o) => o.obstacle_id));
      await run('Hindernis hinzufügen', async () => {
        const updated = await client.addObstacle(garden.share_token, obstacle);
        setGarden(updated);
        // Select what was just placed, so the handles are already on it. The
        // palette promises "then drag the handles"; without this the user has
        // to find and click the thing they are looking straight at.
        const fresh = updated.obstacles.find((o) => !before.has(o.obstacle_id));
        if (fresh !== undefined) setSelectedObstacleId(fresh.obstacle_id);
        const lit = updated.beds
          .map((b) => (b.sun_hours === null ? '?' : b.sun_hours.toFixed(1)))
          .join(', ');
        setStatus(`Hindernis gesetzt. Sonnenstunden jetzt: ${lit}.`);
      });
    },
    [garden, run],
  );

  /**
   * A drawn shape becomes an element with no kind yet.
   *
   * `other` and no height, which casts no shadow: the order the user asked for
   * is draw first and say what it is afterwards, so a half-finished plan must
   * not claim a shading effect nobody described.
   */
  const drawShape = useCallback(
    async (shape: DrawnShape) => {
      setTool(null);
      await addObstacle({
        kind: 'other',
        x: shape.x,
        y: shape.y,
        shape: shape.shape,
        ...(shape.width === null ? {} : { width: shape.width }),
        ...(shape.depth === null ? {} : { depth: shape.depth }),
        ...(shape.points === null ? {} : { points: shape.points }),
      });
    },
    [addObstacle],
  );

  const resizeObstacle = useCallback(
    async (obstacleId: number, box: Box) => {
      if (garden === null) return;
      await run('Größe ändern', async () => {
        const updated = await client.editObstacle(garden.share_token, obstacleId, {
          x: Math.round(box.x * 100) / 100,
          y: Math.round(box.y * 100) / 100,
          width: Math.round(box.width * 100) / 100,
          depth: Math.round(box.depth * 100) / 100,
          rotation: Math.round(box.rotation * 10) / 10,
        });
        setGarden(updated);
      });
    },
    [garden, run],
  );

  /**
   * The logo goes home. Leaving a garden must not lose it — which is exactly why
   * its id is on screen the whole time it is open.
   */
  const goHome = () => {
    window.location.hash = '';
    setGarden(null);
    setSelectedBedId(null);
    setSuggestions(null);
    setTimeline(null);
    setScore(null);
    setImprovements(null);
    setPalette(null);
    setEditing(null);
    setStatus('');
  };

  return (
    <>
      <a className="skip-link" href="#main">Zum Inhalt springen</a>
      <header className="site-header">
        <button type="button" className="brand" onClick={goHome} aria-label="Zur Startseite">
          <svg className="brand__mark" viewBox="0 0 64 64" aria-hidden="true">
            <path className="mark__leaf" d="M32 58C32 40 40 26 56 20 56 40 46 54 32 58Z" />
            <path className="mark__leaf mark__leaf--alt" d="M32 58C32 40 24 26 8 20 8 40 18 54 32 58Z" />
            <path className="mark__stem" d="M32 58V30" />
            <path className="mark__letters" d="M14 24V8l12 16V8M38 24V8l12 16V8" />
          </svg>
          <span className="brand__name">NinaNatur</span>
        </button>
        {version !== null ? (
          <span className="badge" title="Version · Wave · Merges auf main">{version}</span>
        ) : null}
      </header>

      <main id="main" className="layout">
        {garden === null ? (
          <Landing
            createForm={<NewGardenForm onCreate={createGarden} busy={busy} />}
            mapPicker={
              <MapPicker
                onCreate={createFromMap}
                busy={busy}
                search={findPlaces}
                findImagery={findImagery}
              />
            }
            onOpen={(token) => {
              // Into the fragment, so a reload keeps the garden — and the
              // fragment specifically, because the token is a credential and a
              // query parameter would put it in the access log and in any
              // referrer this page sends.
              window.location.hash = token;
              void load(token);
            }}
            busy={busy}
            loadStats={loadStats}
            problem={openProblem}
            accountPanel={
              <AccountPanel
                account={account}
                onRegister={register}
                onLogin={logIn}
                onLogout={logOut}
                busy={busy}
              />
            }
          />
        ) : (
          <>
            <div className="column">
              <GardenId token={garden.share_token} />
              {account !== null ? (
                <button type="button" className="link-button" onClick={claim}>
                  Diesen Garten meinem Konto zuordnen
                </button>
              ) : null}
              {sightlines !== null ? (
                <Sightlines
                  result={sightlines}
                  onClear={() => {
                    setSightlines(null);
                    setViewpoint(null);
                  }}
                />
              ) : null}
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
              <ShapeTools active={tool} onPick={setTool} disabled={busy} />
              <GardenCanvas
                garden={garden}
                selectedBedId={selectedBedId}
                onSelectBed={selectBed}
                onDrawBed={drawBed}
                onSelectObstacle={editObstacleById}
                palette={monthColours}
                viewpoint={viewpoint}
                onPlaceViewpoint={lookFrom}
                tool={tool}
                onDrawShape={drawShape}
                selectedObstacleId={selectedObstacleId}
                onResizeObstacle={resizeObstacle}
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
