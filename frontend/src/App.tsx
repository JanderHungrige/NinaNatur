import { useCallback, useEffect, useMemo, useState } from 'react';

import type {
  BedSuggestions,
  LightMap,
  ShadowDay,
  Terrain,
  ChangeOut,
  BloomPalette,
  FeedbackQuestions,
  GardenOut,
  SightlinesOut,
  SuggestionFilters,
  ImprovementsOut,
  OwnedGardens,
  ScoreOut,
  TimelineOut,
} from './api/client';
import { NinaNaturClient } from './api/client';
import { BedPanel } from './components/BedPanel';
import { AccountBar } from './components/AccountBar';
import { clustersFor } from './canvas/clusters';
import { elementById } from './canvas/elements';
import { useUndoShortcut, useUndoStack } from './useUndoStack';
import { isGround } from './kinds';
import { FeedbackBox } from './components/FeedbackBox';
import { LivingBackground } from './components/LivingBackground';
import { MyGardens } from './components/MyGardens';
import { AccountPanel, type AccountInfo } from './components/AccountPanel';
import { BloomPlayer } from './components/BloomPlayer';
import { ShadeSwitch } from './components/ShadeSwitch';
import type { MapMode } from './components/SunMap';
import { BloomTimeline } from './components/BloomTimeline';
import { GardenCanvas } from './components/GardenCanvas';
import { ColourNote } from './components/ColourNote';
import { ElementList, areaOf } from './components/ElementList';
import { ElementMenu } from './components/ElementMenu';
import { GardenSoil } from './components/GardenSoil';
import { ShapeTools } from './components/ShapeTools';
import { type Panel, Tabs } from './components/Tabs';
import { GardenId } from './components/GardenId';
import { objects } from './plural';
import { Landing } from './components/Landing';
import { MapPicker, type MapSelection } from './components/MapPicker';
import { Sightlines } from './components/Sightlines';
import { BedPlantings } from './components/BedPlantings';
import { ExistingPlanting } from './components/ExistingPlanting';
import { type Box, boxOf, rescale } from './canvas/handles';
import type { DrawnShape, Tool } from './canvas/shapes';
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
  const [infoFor, setInfoFor] = useState<{
    taxonId: number;
    name: string;
    /** What the catalogue says, if anything. */
    recorded: string | null;
    /** What this garden noted, if anything. */
    noted: string | null;
  } | null>(null);
  const [improvements, setImprovements] = useState<ImprovementsOut | null>(null);
  const [filters, setFilters] = useState<SuggestionFilters>({});
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



  /** Which patch of plants is selected, if any. Separate from the bed and the
   *  shape: three things can be picked on this plan and they are not the same
   *  question. */
  const [selectedPlantingId, setSelectedPlantingId] = useState<number | null>(null);
  /** What Ctrl+C put aside: a species and how many of it, not a row id. */
  const [copied, setCopied] = useState<{ taxonId: number | null; rawName: string | null; quantity: number; name: string } | null>(null);

  /** The sun map, and whether it is being shown. Fetched with the garden so the
   *  switch can say straight away whether there is anything to show. */
  const [lightMap, setLightMap] = useState<LightMap | null>(null);
  const [terrain, setTerrain] = useState<Terrain | null>(null);
  const [shadeOn, setShadeOn] = useState(false);
  const [mapMode, setMapMode] = useState<MapMode>('sun');
  /** A day's shadows, and which frame is showing. Fetched only when the day is
   *  actually being watched — it is a request nobody asks for by opening a
   *  garden. */
  const [day, setDay] = useState<ShadowDay | null>(null);
  const [frame, setFrame] = useState(0);

  const { remember, undo, forget } = useUndoStack();

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
    //
    // The same trap caught the sun map on the day it was written — the switch
    // said "nothing drawn yet" for a garden that plainly had a map. Anything
    // fetched in `refresh` and not here is invisible until the first edit.
    setPalette(await client.bloom(token));
    setLightMap(await client.lightMap(token));
    setTerrain(await client.terrain(token));
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

  // Asked whenever there is somebody to ask about, and again after a change.
  // The endpoint has existed since Wave 9; nothing had ever displayed it.
  const loadMyGardens = useCallback(async () => {
    if (account === null) {
      setMyGardens(null);
      return;
    }
    try {
      setMyGardens((await client.myGardens()).gardens);
    } catch {
      // Not being able to list them is not a reason to break the page: the
      // share link still opens a garden, which is what it is for.
      setMyGardens([]);
    }
  }, [account]);

  // Also when a garden closes: coming back to the front door after making or
  // deleting one must show what is actually there, not what was there when the
  // page loaded.
  const onFrontDoor = garden === null;
  useEffect(() => {
    if (onFrontDoor) void loadMyGardens();
  }, [loadMyGardens, onFrontDoor]);

  /** Open one by its token — the same route the landing form takes, since the
   *  token is the credential either way. */
  const openGarden = useCallback(
    (token: string) => {
      // Into the fragment, not a query parameter: the token is a credential,
      // and a query would put it in the access log and any referrer.
      window.location.hash = token;
      void load(token);
    },
    [load],
  );

  const deleteMyGarden = useCallback(
    (token: string) => {
      void run('Garten löschen', async () => {
        await client.deleteGarden(token);
        await loadMyGardens();
        setStatus('Garten gelöscht.');
      });
    },
    [loadMyGardens, run],
  );

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
      // And as a shape, so the handles appear. Clicking a bed used to set only
      // the planting selection, which is the other half of why a bed could not
      // be reshaped: the lookup was wrong *and* nothing ever selected it.
      setSelectedObstacleId(bedId);
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
  // The inverses are calls against one garden. Replayed against another they
  // would edit an element that is not there — or, worse, one that is.
  useEffect(() => {
    forget();
  }, [garden?.share_token, forget]);

  /**
   * The day's shadows, fetched when somebody actually wants to watch them.
   *
   * Not with the garden: it is a request for a thing nobody has asked for by
   * opening a plan. The month follows the filter, so switching months while
   * watching moves the shadows rather than needing a second control.
   */
  useEffect(() => {
    if (garden === null || !shadeOn) {
      setDay(null);
      return;
    }
    const month = filters.floweringMonth ?? 6;
    let dropped = false;
    void client
      .shadowDay(garden.share_token, month)
      .then((fetched) => {
        if (dropped) return;
        setDay(fetched);
        setFrame(0);
      })
      .catch(() => {
        if (!dropped) setDay(null);
      });
    return () => {
      // A month switched twice in a second must not have the first answer
      // arrive last and win.
      dropped = true;
    };
  }, [garden?.share_token, shadeOn, filters.floweringMonth, garden]);

  useUndoShortcut(() => {
    void run('Rückgängig', async () => {
      const entry = await undo();
      setStatus(
        entry === null
          ? 'Nichts mehr zurückzunehmen.'
          : `${entry.label} zurückgenommen.`,
      );
    });
  }, garden !== null);

  const refresh = useCallback(async (token: string, weighted: boolean) => {
    setLightMap(await client.lightMap(token));
    // The ground changes only when it is first fetched, which happens on the
    // recompute button — so this is nearly always the same answer. It is here
    // anyway, because the alternative is the map being right and the relief
    // being a version behind, which is exactly the bug the comment on `load`
    // was written about.
    setTerrain(await client.terrain(token));
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
  /**
   * Every planting in the garden, as a patch ready to draw.
   *
   * Built here rather than in the canvas because it needs two things the canvas
   * does not have: the palette, and which month is being shown. Grey when no
   * month is selected, which is the honest reading of "what is in this bed"
   * outside the bloom year.
   */
  /**
   * The colour that actually applies to each species, hand entry included.
   *
   * The info panel needs it to tell the two states apart: "you entered violet"
   * and "you entered violet and a source has since said blue". Read from the
   * palette, which is where colour is resolved.
   */
  const resolvedColours = useMemo(() => {
    const map: Record<number, string | null> = {};
    for (const bed of palette?.beds ?? []) {
      for (const entry of bed.plantings) {
        if (entry.taxon_id !== null) map[entry.taxon_id] = entry.colour;
      }
    }
    return map;
  }, [palette]);

  const clusters = useMemo(() => {
    if (garden === null) return [];
    const byBed = new Map((palette?.beds ?? []).map((b) => [b.bed_id, b.plantings]));
    return garden.beds.flatMap((bed) =>
      clustersFor(
        bed.polygon,
        bed.plantings,
        byBed.get(bed.bed_id) ?? [],
        filters.floweringMonth ?? null,
      ),
    );
  }, [garden, palette, filters.floweringMonth]);

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


  /** The element the palette has armed. Null is the ordinary state: a plan the
   *  user can click without placing anything. */
  const [tool, setTool] = useState<Tool | null>(null);
  /** Which half of the work is showing. Nobody chooses a shape and reads a
   *  bloom timeline in the same breath. */
  const [panel, setPanel] = useState<Panel>('draw');
  /** The account forms, opened from the header rather than sitting in the page. */
  const [accountOpen, setAccountOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  /** What the feedback form should ask. Fetched once, when it is first opened —
   *  nobody should pay for it on a visit that never uses it. */
  const [feedbackQuestions, setFeedbackQuestions] =
    useState<FeedbackQuestions | null>(null);
  /** The gardens this account has claimed. Null until asked. */
  const [myGardens, setMyGardens] = useState<OwnedGardens['gardens'] | null>(null);
  const [selectedObstacleId, setSelectedObstacleId] = useState<number | null>(null);
  /** The context menu, and which element it is asking about. */
  const [asking, setAsking] = useState<
    | {
        id: number;
        kind: string;
        label: string | null;
        area: number;
        plantings: number;
        shape: string;
        roof: string;
        height: number | null;
        width: number | null;
        soilType: string | null;
        moisture: string | null;
        heightAboveGround: number;
        at: { x: number; y: number };
      }
    | null
  >(null);

  const editObstacleById = useCallback(
    (obstacleId: number) => {
      // Beds too. They are elements of kind `bed`, and refusing to select one
      // here is the other half of why a bed could not be reshaped.
      if (garden === null || elementById(garden, obstacleId) === null) return;
      setSelectedObstacleId(obstacleId);
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
        if (fresh !== undefined) {
          setSelectedObstacleId(fresh.obstacle_id);
          const id = fresh.obstacle_id;
          remember({
            label: 'Zeichnen',
            undo: async () => {
              setGarden(await client.deleteObstacle(garden.share_token, id));
            },
          });
        }
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

  /**
   * The outline itself changed.
   *
   * `constraint_hint: null` goes with it: editing a corner is what ends the
   * promise that a rectangle stays square. The geometry does not convert — it
   * was points all along — so only the promise ends.
   */
  /** Remove one element, from wherever it was asked for. */
  /**
   * Copying a patch, and pasting it into whichever bed is selected.
   *
   * The clipboard holds a species and a count, not a planting id: pasting is
   * planting the same thing again, and a row id would be a reference to
   * somebody else's row. Into the same bed it raises the count rather than
   * starting a second patch a metre away — the table says one row per species
   * per bed, and that is what a gardener means by planting more of something.
   */
  const copyCluster = useCallback(() => {
    if (garden === null || selectedPlantingId === null) return;
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
  }, [garden, selectedPlantingId]);

  const pasteCluster = useCallback(() => {
    if (garden === null || copied === null) return;
    if (selectedBedId === null) {
      setStatus('Wähle erst ein Beet, in das gepflanzt werden soll.');
      return;
    }
    const target = selectedBedId;
    void run('Einfügen', async () => {
      const updated =
        copied.taxonId !== null
          ? await client.plant(garden.share_token, target, copied.taxonId, copied.quantity)
          : await client.plantByName(garden.share_token, target, {
              raw_name: copied.rawName ?? copied.name,
              quantity: copied.quantity,
            });
      setGarden(updated);
      await refresh(garden.share_token, forage);
      setSuggestions(
        await client.bedSuggestions(garden.share_token, target, filters),
      );
      setStatus(`${copied.name} eingefügt.`);
    });
  }, [garden, copied, selectedBedId, forage, filters, refresh, run]);

  // Ctrl+C and Ctrl+V on the plan. Not while typing: a name being written in a
  // label field is what those keys mean there.
  useEffect(() => {
    if (garden === null) return;
    const onKey = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey)) return;
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.isContentEditable ||
          ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
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
  }, [garden, selectedPlantingId, copied, copyCluster, pasteCluster]);

  const moveCluster = useCallback(
    (plantingId: number, to: { x: number; y: number }) => {
      if (garden === null) return;
      void run('Verschieben', async () => {
        setGarden(await client.placePlanting(garden.share_token, plantingId, to));
      });
    },
    [garden, run],
  );

  const removePlanting = useCallback(
    (plantingId: number) => {
      if (garden === null) return;
      void run('Pflanze entfernen', async () => {
        setGarden(await client.removePlanting(garden.share_token, plantingId));
        // The bloom year, the insect score and the palette all counted it.
        await refresh(garden.share_token, forage);
        if (selectedBedId !== null) {
          setSuggestions(
            await client.bedSuggestions(garden.share_token, selectedBedId, filters),
          );
        }
      });
    },
    [garden, forage, refresh, run, selectedBedId, filters],
  );

  const deleteElement = useCallback(
    (id: number) => {
      if (garden === null) return;
      setAsking(null);
      setSelectedObstacleId(null);
      void run('Objekt löschen', async () => {
        setGarden(await client.deleteObstacle(garden.share_token, id));
        await refresh(garden.share_token, forage);
      });
    },
    [garden, forage, refresh, run],
  );

  const askWhatItIs = useCallback(
    (id: number, at: { x: number; y: number }) => {
      const found =
        garden?.obstacles.find((o) => o.obstacle_id === id) ??
        garden?.beds.find((b) => b.bed_id === id);
      if (found === undefined) return;
      const outline = 'footprint' in found ? found.footprint : found.polygon;
      setAsking({
        id,
        kind: 'kind' in found ? found.kind : 'bed',
        label: found.label,
        area: areaOf(outline),
        plantings: 'plantings' in found ? found.plantings.length : 0,
        shape: 'shape' in found ? found.shape : 'polygon',
        roof: 'roof' in found ? found.roof : 'unknown',
        height: 'height' in found ? found.height : null,
        width: 'width' in found ? found.width : null,
        soilType: 'soil_type' in found ? found.soil_type : null,
        moisture: 'moisture' in found ? found.moisture : null,
        heightAboveGround:
          'height_above_ground' in found ? found.height_above_ground : 0,
        at,
      });
    },
    [garden],
  );

  const saveGardenSoil = useCallback(
    (soilType: string, moisture: string) => {
      if (garden === null) return;
      void run('Boden speichern', async () => {
        setGarden(await client.setGardenSoil(garden.share_token, soilType, moisture));
      });
    },
    [garden, run],
  );

  /** Dragged to a new place. The outline is untouched; only its origin moves. */
  const moveObstacle = useCallback(
    async (obstacleId: number, by: { x: number; y: number }) => {
      if (garden === null) return;
      const element = elementById(garden, obstacleId);
      // The ground is where everything else is measured from. Moving it would
      // shift the garden out from under the plan rather than move anything in
      // it — and not being able to drag it is behaviour the gardener asked to
      // keep.
      if (element === null || isGround(element.kind)) return;
      const from = { x: element.x, y: element.y };
      await run('Verschieben', async () => {
        setGarden(
          await client.editObstacle(garden.share_token, obstacleId, {
            x: Math.round((element.x + by.x) * 100) / 100,
            y: Math.round((element.y + by.y) * 100) / 100,
          }),
        );
        remember({
          label: 'Verschieben',
          undo: async () => {
            setGarden(
              await client.editObstacle(garden.share_token, obstacleId, from),
            );
          },
        });
      });
    },
    [garden, run],
  );

  const reshapeObstacle = useCallback(
    async (obstacleId: number, points: number[][]) => {
      if (garden === null) return;
      const was = elementById(garden, obstacleId);
      await run('Form ändern', async () => {
        setGarden(
          await client.editObstacle(garden.share_token, obstacleId, {
            points,
            constraint_hint: null,
          }),
        );
        if (was !== null && was.points !== null) {
          const { points: had, constraint_hint: hint } = was;
          remember({
            label: 'Form ändern',
            undo: async () => {
              setGarden(
                await client.editObstacle(garden.share_token, obstacleId, {
                  points: had,
                  constraint_hint: hint,
                }),
              );
            },
          });
        }
      });
    },
    [garden, run],
  );

  /**
   * A freehand stroke becomes an element.
   *
   * A closed loop is an outline; an open stroke is a path — a line with a width
   * rather than twenty points around a one-metre strip. A metre is what a
   * garden path usually is, and it stays editable afterwards.
   */
  const drawTrace = useCallback(
    async (trace: { kind: 'area' | 'path'; points: number[][] }) => {
      setTool(null);
      const centre = trace.points.reduce(
        (acc, p) => ({ x: acc.x + p[0]! / trace.points.length, y: acc.y + p[1]! / trace.points.length }),
        { x: 0, y: 0 },
      );
      await addObstacle({
        kind: trace.kind === 'path' ? 'path' : 'other',
        x: Math.round(centre.x * 100) / 100,
        y: Math.round(centre.y * 100) / 100,
        shape: trace.kind === 'path' ? 'line' : 'polygon',
        ...(trace.kind === 'path' ? { width: 1 } : {}),
        points: trace.points.map((p) => [
          Math.round((p[0]! - centre.x) * 100) / 100,
          Math.round((p[1]! - centre.y) * 100) / 100,
        ]),
      });
    },
    [addObstacle],
  );

  /**
   * A handle was let go: the shape is the same outline at a new size.
   *
   * Scaled points rather than a width and an angle. The server can only apply
   * those to a rectangle, so for a triangle or a freehand outline they meant
   * the points were discarded — and reading the garden afterwards raised.
   */
  const resizeObstacle = useCallback(
    async (obstacleId: number, box: Box) => {
      if (garden === null) return;
      const element = elementById(garden, obstacleId);
      // Same rule as moving: the ground is not dragged about by its handles.
      if (element === null || isGround(element.kind)) return;
      const at = {
        x: Math.round(box.x * 100) / 100,
        y: Math.round(box.y * 100) / 100,
      };
      await run('Größe ändern', async () => {
        setGarden(
          await client.editObstacle(
            garden.share_token,
            obstacleId,
            element.points === null
              ? // A circle has a diameter and no corners to move.
                { ...at, width: Math.round(box.width * 100) / 100 }
              : { ...at, points: rescale(element.points, boxOf(element), box) },
          ),
        );
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
    setStatus('');
  };

  return (
    // The front door is dark all the way out to the edges; a garden is not.
    <div className={garden === null ? 'app app--front-door' : 'app'}>
      <a className="skip-link" href="#main">Zum Inhalt springen</a>
      {garden === null && <LivingBackground videoSrc="/meadow.mp4" />}
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
        <button
          type="button"
          className="header-link"
          onClick={() => {
            setFeedbackOpen(true);
            if (feedbackQuestions === null) {
              void client.feedbackQuestions().then(setFeedbackQuestions).catch(() => undefined);
            }
          }}
        >
          Rückmeldung
        </button>
        <AccountBar
          username={account?.username ?? null}
          onSignIn={() => setAccountOpen(true)}
          onSignUp={() => setAccountOpen(true)}
          onSignOut={() => void logOut()}
          inviting={garden === null && account === null}
          busy={busy}
        />
      </header>

      {feedbackOpen && (
        <div className="account-drawer">
          <FeedbackBox
            questions={feedbackQuestions}
            onSend={async (kind, answers) => {
              const sent = await client.sendFeedback(kind, answers);
              return sent.message;
            }}
            onClose={() => setFeedbackOpen(false)}
          />
        </div>
      )}

      {accountOpen && account === null && (
        <div className="account-drawer">
          <AccountPanel
            account={account}
            onRegister={async (input) => {
              await register(input);
              setAccountOpen(false);
            }}
            onLogin={async (input) => {
              await logIn(input);
              setAccountOpen(false);
            }}
            onLogout={logOut}
            busy={busy}
          />
          <button type="button" className="link-button" onClick={() => setAccountOpen(false)}>
            Schließen
          </button>
        </div>
      )}

      {/* Not `layout`: that is the garden's two-column grid, and the landing
          page rendered inside it was handed the 22rem sidebar column — 352 px
          of landing page on a 1600 px window, correct again only when the
          window was made smaller than the breakpoint. */}
      <main id="main" className={garden === null ? 'landing-shell' : 'layout'}>
        {garden === null ? (
          <Landing
            myGardens={
              account === null || myGardens === null ? undefined : (
                <MyGardens
                  gardens={myGardens}
                  onOpen={openGarden}
                  onDelete={deleteMyGarden}
                  busy={busy}
                />
              )
            }
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
          />
        ) : (
          <>
            <div className="column">
              <GardenId
                token={garden.share_token}
                name={garden.name}
                latitude={garden.latitude}
                longitude={garden.longitude}
              />
              <Tabs active={panel} onPick={setPanel} />

              <div
                id="panel-draw"
                role="tabpanel"
                aria-labelledby="tab-draw"
                hidden={panel !== 'draw'}
              >
              <ShapeTools active={tool} onPick={setTool} disabled={busy} />
              <GardenSoil
                soilType={garden.soil_type}
                moisture={garden.moisture}
                onSave={saveGardenSoil}
                busy={busy}
              />
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
              />
              <ShadeSwitch
                map={lightMap}
                terrain={terrain}
                on={shadeOn}
                mode={mapMode}
                onToggle={(next) => {
                  setShadeOn(next);
                  // Leaving the map also leaves the day: the two are one
                  // question, and a day playing behind a hidden map is a timer
                  // nobody can see.
                  if (!next) setDay(null);
                }}
                onMode={setMapMode}
                onRebuild={() =>
                  void run('Schatten neu berechnen', async () => {
                    setLightMap(await client.rebuildLightMap(garden.share_token));
                  })
                }
                busy={busy}
              />
              <ElementList
                garden={garden}
                onDelete={deleteElement}
                selectedId={selectedObstacleId ?? selectedBedId}
                onSelect={(id) => {
                  // One selection, whichever way it was reached — the plan and
                  // the list disagreeing about what is selected is the obvious
                  // way for two panels onto the same thing to go wrong.
                  const isBed = garden.beds.some((b) => b.bed_id === id);
                  if (isBed) {
                    selectBed(id);
                    setSelectedObstacleId(null);
                  } else {
                    editObstacleById(id);
                  }
                }}
              />
              </div>

              <div
                id="panel-sow"
                role="tabpanel"
                aria-labelledby="tab-sow"
                hidden={panel !== 'sow'}
              >
              {selectedBedId !== null ? (
                <>
                  {(() => {
                    const bed = garden.beds.find((b) => b.bed_id === selectedBedId);
                    return bed === undefined ? null : (
                      <BedPlantings
                        bed={bed}
                        onRemove={removePlanting}
                        onShowInfo={(taxonId, name) =>
                          setInfoFor({
                            taxonId,
                            name,
                            recorded: resolvedColours[taxonId] ?? null,
                            noted: garden.observed_colours[taxonId] ?? null,
                          })
                        }
                        busy={busy}
                      />
                    );
                  })()}
                  <ExistingPlanting
                    onAdd={addExisting}
                    unidentified={garden.unidentified_plantings}
                    busy={busy}
                  />
                </>
              ) : null}
              <FilterControls filters={filters} onChange={changeFilters} disabled={busy} />
              <FilterBar
                filters={filters}
                counts={suggestions?.filters ?? {}}
                onChange={changeFilters}
              />
              {infoFor !== null ? (
                <SpeciesInfo
                  taxonId={infoFor.taxonId}
                  canonicalName={infoFor.name}
                  onClose={() => setInfoFor(null)}
                  colourNote={
                    <ColourNote
                      recorded={infoFor.recorded}
                      noted={infoFor.noted}
                      busy={busy}
                      onNote={(colour) => {
                        const asked = infoFor;
                        void run('Blütenfarbe merken', async () => {
                          setGarden(
                            await client.noteColour(
                              garden.share_token,
                              asked.taxonId,
                              colour,
                            ),
                          );
                          await refresh(garden.share_token, forage);
                          // The list is where the colour was missing from, and
                          // `refresh` does not re-read it: without this the row
                          // still said "Farbe unbekannt" after the panel closed.
                          if (selectedBedId !== null) {
                            setSuggestions(
                              await client.bedSuggestions(
                                garden.share_token,
                                selectedBedId,
                                filters,
                              ),
                            );
                          }
                          // Only once it is stored. Setting it first showed
                          // "von dir eingetragen" over a 405 for a route that
                          // was mounted at the wrong path.
                          setInfoFor({ ...asked, noted: colour });
                        });
                      }}
                    />
                  }
                />
              ) : null}
              <SuggestionList
                includeTrees={filters.includeTrees !== false}
                suggestions={suggestions}
                onPlant={plant}
                onShowInfo={(taxonId, name, recorded) =>
                  setInfoFor({
                    taxonId,
                    name,
                    recorded,
                    noted: garden.observed_colours[taxonId] ?? null,
                  })
                }
                busy={busy}
              />
              </div>
            </div>
            <div className="column">
              <GardenCanvas
                garden={garden}
                selectedBedId={selectedBedId}
                onSelectBed={selectBed}
                onDrawBed={drawBed}
                onSelectObstacle={editObstacleById}
                clusters={clusters}
                selectedPlantingId={selectedPlantingId}
                onSelectCluster={setSelectedPlantingId}
                onMoveCluster={moveCluster}
                terrain={shadeOn ? terrain : null}
                sunMap={
                  shadeOn && lightMap !== null
                    ? { map: lightMap, mode: mapMode }
                    : undefined
                }
                shadows={day?.frames[frame]?.polygons ?? undefined}
                onShowClusterInfo={(taxonId, name) =>
                  setInfoFor({
                    taxonId,
                    name,
                    recorded: resolvedColours[taxonId] ?? null,
                    noted: garden.observed_colours[taxonId] ?? null,
                  })
                }
                viewpoint={viewpoint}
                onPlaceViewpoint={lookFrom}
                tool={tool}
                onDrawShape={drawShape}
                onDrawTrace={drawTrace}
                onCancelTool={() => setTool(null)}
                onClearSelection={() => {
                  setSelectedObstacleId(null);
                  setAsking(null);
                }}
                onAskWhatItIs={askWhatItIs}
                selectedObstacleId={selectedObstacleId}
                onResizeObstacle={resizeObstacle}
                onMoveObstacle={moveObstacle}
                onReshapeObstacle={reshapeObstacle}
              />
              {asking !== null && garden !== null ? (
                <ElementMenu
                  elementId={asking.id}
                  at={asking.at}
                  kind={asking.kind}
                  label={asking.label}
                  area={asking.area}
                  plantings={asking.plantings}
                  shape={asking.shape}
                  roof={asking.roof}
                  height={asking.height}
                  width={asking.width}
                  soilType={asking.soilType}
                  moisture={asking.moisture}
                  heightAboveGround={asking.heightAboveGround}
                  busy={busy}
                  onDelete={() => deleteElement(asking.id)}
                  onClose={() => setAsking(null)}
                  onSave={(changes) => {
                    const target = asking.id;
                    void run('Speichern', async () => {
                      setGarden(
                        await client.editObstacle(garden.share_token, target, changes),
                      );
                      await refresh(garden.share_token, forage);
                      // Closed only once it worked. Closing first meant a
                      // failure left nothing on screen but a status line, and
                      // the shape looking exactly as it had.
                      setAsking(null);
                    });
                  }}
                />
              ) : null}

              {timeline !== null ? (
                <>
                <BloomPlayer
                  shadowDay={
                    shadeOn && day !== null
                      ? {
                          frames: day.frames.length,
                          frame,
                          onFrame: setFrame,
                        }
                      : undefined
                  }
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
    </div>
  );
}
