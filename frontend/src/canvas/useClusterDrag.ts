import { useEffect, useRef, useState } from 'react';

import { type Cluster, keepInside } from './clusters';
import { type Point, type Viewport, toGarden } from './viewport';

interface Options {
  view: Viewport;
  surface: React.RefObject<SVGSVGElement | null>;
  clusters: Cluster[];
  /** The bed each cluster belongs to, as an outline in absolute metres. */
  bedOf: (plantingId: number) => Point[] | null;
  onFinish: (plantingId: number, to: Point) => void;
}

/**
 * Dragging a patch of plants around inside its bed.
 *
 * Separate from `useElementDrag` because the two mean different things. Moving
 * a shape is a delta the server adds to an origin; moving a cluster is an
 * absolute position inside a bed, and it is clamped to that bed's outline —
 * not its bounding box, because the notch of an L-shaped bed is not in the bed.
 *
 * The clamping happens while dragging as well as at the end, so the patch never
 * appears outside the bed even for a frame.
 */
export function useClusterDrag(options: Options) {
  const [dragging, setDragging] = useState<{ id: number; at: Point } | null>(null);
  const held = useRef<{ id: number; grabOffset: Point; moved: boolean } | null>(null);
  const latest = useRef<Point | null>(null);

  const metres = (event: { clientX: number; clientY: number }): Point => {
    const rect = options.surface.current?.getBoundingClientRect();
    return toGarden(
      { x: event.clientX - (rect?.left ?? 0), y: event.clientY - (rect?.top ?? 0) },
      options.view,
    );
  };

  const grab = (plantingId: number, event: React.PointerEvent) => {
    const cluster = options.clusters.find((c) => c.plantingId === plantingId);
    if (cluster === undefined) return;
    // Otherwise the bed underneath reads this as the start of its own drag, and
    // the whole bed moves while the gardener is moving one patch in it.
    event.stopPropagation();
    const at = metres(event);
    held.current = {
      id: plantingId,
      // Grabbed by the point that was under the pointer, not by the middle: a
      // patch that jumps so its centre meets the cursor is a patch that moved
      // before the drag began.
      grabOffset: { x: cluster.centre.x - at.x, y: cluster.centre.y - at.y },
      moved: false,
    };
    latest.current = cluster.centre;
    setDragging({ id: plantingId, at: cluster.centre });
  };

  useEffect(() => {
    if (dragging === null) return undefined;

    const onMove = (event: PointerEvent) => {
      const active = held.current;
      if (active === null) return;
      const pointer = metres(event);
      const wanted = {
        x: pointer.x + active.grabOffset.x,
        y: pointer.y + active.grabOffset.y,
      };
      const outline = options.bedOf(active.id);
      const at = outline === null ? wanted : keepInside(outline, wanted);
      active.moved = true;
      latest.current = at;
      setDragging({ id: active.id, at });
    };

    const onUp = () => {
      const active = held.current;
      const at = latest.current;
      held.current = null;
      setDragging(null);
      // A click selects a patch. Saving a move of nothing still costs a request
      // and a re-read of the whole garden.
      if (active === null || at === null || !active.moved) return;
      options.onFinish(active.id, {
        x: Math.round(at.x * 100) / 100,
        y: Math.round(at.y * 100) / 100,
      });
    };

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [dragging, options]);

  return { dragging, grab };
}
