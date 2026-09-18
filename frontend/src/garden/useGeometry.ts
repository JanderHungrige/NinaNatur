import { useCallback } from 'react';

import type { GardenOut, NinaNaturClient } from '../api/client';
import { elementById } from '../canvas/elements';
import { type Box, boxOf, rescale } from '../canvas/handles';
import { isFixed } from '../kinds';
import type { UndoEntry } from '../useUndoStack';
import type { Status } from '../useStatus';

/**
 * The three edits to an element's geometry: move, reshape, resize (doc 87).
 * Move and reshape remember how to take themselves back.
 *
 * None of them applies to what stays where it is: the ground, and the houses
 * and streets around it (doc 87, B1). The plan offers no drag, handle or corner
 * for those; this is the same rule where the request is made.
 */
export function useGeometry(
  client: NinaNaturClient,
  garden: GardenOut,
  setGarden: (garden: GardenOut) => void,
  status: Status,
  remember: (entry: UndoEntry) => void,
) {
  const { run } = status;
  const token = garden.share_token;

  /** Dragged to a new place. The outline is untouched; only its origin moves. */
  const moveObstacle = useCallback(
    async (obstacleId: number, by: { x: number; y: number }) => {
      const element = elementById(garden, obstacleId);
      // The ground is where everything else is measured from, and the houses
      // and streets are where they are. Not being able to drag any of them is
      // behaviour the gardener asked for.
      if (element === null || isFixed(element.kind)) return;
      const from = { x: element.x, y: element.y };
      await run('Verschieben', async () => {
        setGarden(
          await client.editObstacle(token, obstacleId, {
            x: Math.round((element.x + by.x) * 100) / 100,
            y: Math.round((element.y + by.y) * 100) / 100,
          }),
        );
        remember({
          label: 'Verschieben',
          undo: async () => {
            setGarden(await client.editObstacle(token, obstacleId, from));
          },
        });
      });
    },
    [client, token, garden, run, setGarden, remember],
  );

  /**
   * The outline itself changed.
   *
   * `constraint_hint: null` goes with it: editing a corner is what ends the
   * promise that a rectangle stays square.
   */
  const reshapeObstacle = useCallback(
    async (obstacleId: number, points: number[][]) => {
      const was = elementById(garden, obstacleId);
      // Same rule as moving: a house's or a street's corners stay where they are.
      if (was !== null && isFixed(was.kind)) return;
      await run('Form ändern', async () => {
        setGarden(await client.editObstacle(token, obstacleId, { points, constraint_hint: null }));
        if (was !== null && was.points !== null) {
          const { points: had, constraint_hint: hint } = was;
          remember({
            label: 'Form ändern',
            undo: async () => {
              setGarden(
                await client.editObstacle(token, obstacleId, { points: had, constraint_hint: hint }),
              );
            },
          });
        }
      });
    },
    [client, token, garden, run, setGarden, remember],
  );

  /**
   * A handle was let go: the shape is the same outline at a new size.
   *
   * Scaled points rather than a width and an angle. The server can only apply
   * those to a rectangle, so for a triangle or a freehand outline they meant the
   * points were discarded — and reading the garden afterwards raised.
   */
  const resizeObstacle = useCallback(
    async (obstacleId: number, box: Box) => {
      const element = elementById(garden, obstacleId);
      // Same rule as moving: nothing fixed is dragged about by its handles.
      if (element === null || isFixed(element.kind)) return;
      const at = { x: Math.round(box.x * 100) / 100, y: Math.round(box.y * 100) / 100 };
      await run('Größe ändern', async () => {
        setGarden(
          await client.editObstacle(
            token,
            obstacleId,
            element.points === null
              ? // A circle has a diameter and no corners to move.
                { ...at, width: Math.round(box.width * 100) / 100 }
              : { ...at, points: rescale(element.points, boxOf(element), box) },
          ),
        );
      });
    },
    [client, token, garden, run, setGarden],
  );

  return { moveObstacle, reshapeObstacle, resizeObstacle };
}
