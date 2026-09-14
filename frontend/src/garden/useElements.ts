import { useCallback, useState } from 'react';

import type { GardenOut, NinaNaturClient } from '../api/client';
import { elementById } from '../canvas/elements';
import type { DrawnShape, Tool } from '../canvas/shapes';
import { areaOf } from '../components/ElementList';
import type { UndoEntry } from '../useUndoStack';
import type { Status } from '../useStatus';

/** The context menu, and which element it is asking about. */
export interface Asking {
  id: number;
  kind: string;
  label: string | null;
  area: number;
  plantings: number;
  shape: string;
  roof: string;
  eavesM: number | null;
  height: number | null;
  width: number | null;
  soilType: string | null;
  moisture: string | null;
  heightAboveGround: number;
  at: { x: number; y: number };
}

type NewObstacle = {
  kind: string;
  x: number;
  y: number;
  shape?: string;
  width?: number;
  depth?: number;
  points?: number[][];
  height?: number;
};

type ElementChanges = Parameters<NinaNaturClient['editObstacle']>[2];

/**
 * Drawing elements and saying what they are: the armed tool, the element being
 * edited, the menu asking about one, and every call that adds, names or removes
 * something (doc 87).
 */
export function useElements(
  client: NinaNaturClient,
  garden: GardenOut,
  setGarden: (garden: GardenOut) => void,
  status: Status,
  refresh: () => Promise<void>,
  remember: (entry: UndoEntry) => void,
) {
  const { run, setStatus } = status;
  const token = garden.share_token;
  /** The tool the rail has armed. Null is the ordinary state: a plan the user
   *  can click without placing anything. */
  const [tool, setTool] = useState<Tool | null>(null);
  const [selectedObstacleId, setSelectedObstacleId] = useState<number | null>(null);
  const [asking, setAsking] = useState<Asking | null>(null);

  const editObstacleById = useCallback(
    (obstacleId: number) => {
      // Beds too. They are elements of kind `bed`, and refusing to select one
      // here is the other half of why a bed could not be reshaped.
      if (elementById(garden, obstacleId) === null) return;
      setSelectedObstacleId(obstacleId);
    },
    [garden],
  );

  const addBed = useCallback(
    async (bed: { name: string; polygon: number[][]; soil_type: string; moisture: string }) => {
      await run('Beet hinzufügen', async () => {
        // Re-render from the server's answer rather than local optimism: only the
        // server can compute light, and guessing it here would show a number the
        // data does not support.
        setGarden(await client.addBed(token, bed));
        await refresh();
        setStatus(`Beet ${bed.name} hinzugefügt.`);
      });
    },
    [client, token, run, setGarden, refresh, setStatus],
  );

  /** A polygon drawn on the plan becomes a bed with a placeholder name and the
   *  default soil. Asking for a name mid-drawing would interrupt the one gesture
   *  the whole feature exists for. */
  const drawBed = useCallback(
    (polygon: number[][]) => {
      void addBed({
        name: `Beet ${garden.beds.length + 1}`,
        polygon,
        soil_type: 'loam',
        moisture: 'fresh',
      });
    },
    [garden, addBed],
  );

  const addObstacle = useCallback(
    async (obstacle: NewObstacle) => {
      const before = new Set(garden.obstacles.map((o) => o.obstacle_id));
      await run('Hindernis hinzufügen', async () => {
        const updated = await client.addObstacle(token, obstacle);
        setGarden(updated);
        // Select what was just placed, so the handles are already on it.
        const fresh = updated.obstacles.find((o) => !before.has(o.obstacle_id));
        if (fresh !== undefined) {
          setSelectedObstacleId(fresh.obstacle_id);
          const id = fresh.obstacle_id;
          remember({
            label: 'Zeichnen',
            undo: async () => {
              setGarden(await client.deleteObstacle(token, id));
            },
          });
        }
        const lit = updated.beds
          .map((b) => (b.sun_hours === null ? '?' : b.sun_hours.toFixed(1)))
          .join(', ');
        setStatus(`Hindernis gesetzt. Sonnenstunden jetzt: ${lit}.`);
      });
    },
    [client, token, garden, run, setGarden, setStatus, remember],
  );

  /** A drawn shape becomes an element with no kind yet: `other` and no height,
   *  which casts no shadow. Draw first, say what it is afterwards. */
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

  /** A freehand stroke becomes an element: a closed loop is an outline, an open
   *  stroke a path — a line one metre wide, and editable afterwards. */
  const drawTrace = useCallback(
    async (trace: { kind: 'area' | 'path'; points: number[][] }) => {
      setTool(null);
      const centre = trace.points.reduce(
        (acc, p) => ({
          x: acc.x + p[0]! / trace.points.length,
          y: acc.y + p[1]! / trace.points.length,
        }),
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

  /** Remove one element, from wherever it was asked for. */
  const deleteElement = useCallback(
    (id: number) => {
      setAsking(null);
      setSelectedObstacleId(null);
      void run('Objekt löschen', async () => {
        setGarden(await client.deleteObstacle(token, id));
        await refresh();
      });
    },
    [client, token, run, setGarden, refresh],
  );

  const askWhatItIs = useCallback(
    (id: number, at: { x: number; y: number }) => {
      const found =
        garden.obstacles.find((o) => o.obstacle_id === id) ?? garden.beds.find((b) => b.bed_id === id);
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
        // Only one of a bed and an obstacle has eaves, so the narrowing has to
        // be explicit rather than a `??`.
        eavesM: 'eaves_m' in found && typeof found.eaves_m === 'number' ? found.eaves_m : null,
        height: 'height' in found ? found.height : null,
        width: 'width' in found ? found.width : null,
        soilType: 'soil_type' in found ? found.soil_type : null,
        moisture: 'moisture' in found ? found.moisture : null,
        heightAboveGround: 'height_above_ground' in found ? found.height_above_ground : 0,
        at,
      });
    },
    [garden],
  );

  /** The element menu's answer. Closed only once it worked: closing first left
   *  nothing on screen after a failure but the shape looking as it had. */
  const saveElement = useCallback(
    (changes: ElementChanges) => {
      if (asking === null) return;
      const target = asking.id;
      void run('Speichern', async () => {
        setGarden(await client.editObstacle(token, target, changes));
        await refresh();
        setAsking(null);
      });
    },
    [client, token, asking, run, setGarden, refresh],
  );

  const saveGardenSoil = useCallback(
    (soilType: string, moisture: string) => {
      void run('Boden speichern', async () => {
        setGarden(await client.setGardenSoil(token, soilType, moisture));
      });
    },
    [client, token, run, setGarden],
  );

  const claim = useCallback(() => {
    void run('Übernehmen', async () => {
      setGarden(await client.claimGarden(token));
      setStatus('Dieser Garten gehört jetzt zu deinem Konto.');
    });
  }, [client, token, run, setGarden, setStatus]);

  return {
    tool,
    setTool,
    selectedObstacleId,
    setSelectedObstacleId,
    asking,
    setAsking,
    editObstacleById,
    drawBed,
    drawShape,
    drawTrace,
    deleteElement,
    askWhatItIs,
    saveElement,
    saveGardenSoil,
    claim,
  };
}

export type Elements = ReturnType<typeof useElements>;
