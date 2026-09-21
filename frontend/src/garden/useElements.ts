import { useCallback, useState } from 'react';

import type { GardenOut, NinaNaturClient } from '../api/client';
import type { DrawnShape, Tool } from '../canvas/shapes';
import { labelOf } from '../kinds';
import type { UndoEntry } from '../useUndoStack';
import type { Status } from '../useStatus';

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

/** What drawing needs of the selection: to select what was just drawn, and to
 *  let go of what is deleted (doc 88). */
interface Selecting {
  selectElement: (id: number) => void;
  clear: () => void;
}

/**
 * Drawing elements and saying what they are: the armed tool, and every call that
 * adds, names or removes something (docs 87, 88). Which element is selected is
 * the selection's, not this hook's.
 */
export function useElements(
  client: NinaNaturClient,
  garden: GardenOut,
  setGarden: (garden: GardenOut) => void,
  status: Status,
  refresh: () => Promise<void>,
  remember: (entry: UndoEntry) => void,
  selecting: Selecting,
) {
  const { run, setStatus } = status;
  const { selectElement, clear } = selecting;
  const token = garden.share_token;
  /** The tool the rail has armed. Null is the ordinary state: a plan the user
   *  can click without placing anything. */
  const [tool, setTool] = useState<Tool | null>(null);

  const addBed = useCallback(
    async (bed: { name: string; polygon: number[][]; soil_type: string; moisture: string }) => {
      const before = new Set(garden.beds.map((b) => b.bed_id));
      await run('Beet hinzufügen', async () => {
        // Re-render from the server's answer rather than local optimism: only the
        // server can compute light, and guessing it here would show a number the
        // data does not support.
        const updated = await client.addBed(token, bed);
        setGarden(updated);
        // What was just drawn is selected (doc 88), so the next thing the details
        // show is the bed to plant in.
        const fresh = updated.beds.find((b) => !before.has(b.bed_id));
        if (fresh !== undefined) selectElement(fresh.bed_id);
        await refresh();
        setStatus(`Beet ${bed.name} hinzugefügt.`);
      });
    },
    [client, token, garden, run, setGarden, refresh, setStatus, selectElement],
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
          selectElement(fresh.obstacle_id);
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
    [client, token, garden, run, setGarden, setStatus, remember, selectElement],
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
      const cm = (v: number): number => Math.round(v * 100) / 100;
      // The centre is rounded first, so the corners stored relative to it are
      // exactly the ones drawn. Rounding twice around an unrounded centre could
      // merge two corners a centimetre apart into one.
      const x = cm(trace.points.reduce((sum, p) => sum + p[0]!, 0) / trace.points.length);
      const y = cm(trace.points.reduce((sum, p) => sum + p[1]!, 0) / trace.points.length);
      const points = trace.points.map((p) => [cm(p[0]! - x), cm(p[1]! - y)]);
      const corners = new Set(points.map((p) => `${p[0]},${p[1]}`)).size;
      if (corners < (trace.kind === 'path' ? 2 : 3)) {
        setStatus('Der Strich ist zu kurz — zieh ihn etwas weiter.');
        return;
      }
      await addObstacle({
        kind: trace.kind === 'path' ? 'path' : 'other',
        x,
        y,
        shape: trace.kind === 'path' ? 'line' : 'polygon',
        ...(trace.kind === 'path' ? { width: 1 } : {}),
        points,
      });
    },
    [addObstacle, setStatus],
  );

  /** Remove one element, from wherever it was asked for. */
  const deleteElement = useCallback(
    (id: number) => {
      clear();
      void run('Objekt löschen', async () => {
        setGarden(await client.deleteObstacle(token, id));
        await refresh();
      });
    },
    [client, token, run, setGarden, refresh, clear],
  );

  /** The element form's answer, for the element it was about. The form stays
   *  where it is, so the toast is what says it worked (doc 88). */
  const saveElement = useCallback(
    (id: number, changes: ElementChanges) => {
      void run('Speichern', async () => {
        setGarden(await client.editObstacle(token, id, changes));
        await refresh();
        const kind = typeof changes.kind === 'string' ? changes.kind : null;
        setStatus(`${kind === null ? 'Objekt' : labelOf(kind)} gespeichert.`);
      });
    },
    [client, token, run, setGarden, refresh, setStatus],
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
    drawBed,
    drawShape,
    drawTrace,
    deleteElement,
    saveElement,
    saveGardenSoil,
    claim,
  };
}

export type Elements = ReturnType<typeof useElements>;
