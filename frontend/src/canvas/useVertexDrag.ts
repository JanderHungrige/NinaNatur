/**
 * Dragging one corner of an outline.
 *
 * Kept apart from the resize handles because it means something different: a
 * resize keeps the shape and changes its size, while this changes the shape
 * itself — and on a rectangle it ends the promise that the corners stay square.
 */
import { useEffect, useRef, useState } from 'react';

import { moveVertex } from './vertices';
import { type Point, type Viewport, toGarden } from './viewport';

interface Options {
  points: number[][] | null;
  origin: { x: number; y: number };
  view: Viewport;
  surface: React.RefObject<SVGSVGElement | null>;
  onFinish: (points: number[][]) => void;
}

export function useVertexDrag(options: Options) {
  const [preview, setPreview] = useState<number[][] | null>(null);
  const grabbed = useRef<{ index: number; moved: boolean } | null>(null);
  const latest = useRef<number[][] | null>(null);

  const grab = (index: number, event: React.PointerEvent) => {
    // The surface below would otherwise read this as a click on the plan and
    // start drawing something.
    event.stopPropagation();
    if (options.points === null) return;
    grabbed.current = { index, moved: false };
    latest.current = options.points;
    setPreview(options.points);
  };

  useEffect(() => {
    if (preview === null) return undefined;
    const onMove = (event: PointerEvent) => {
      const active = grabbed.current;
      if (active === null) return;
      active.moved = true;
      const rect = options.surface.current?.getBoundingClientRect();
      const at: Point = toGarden(
        { x: event.clientX - (rect?.left ?? 0), y: event.clientY - (rect?.top ?? 0) },
        options.view,
      );
      latest.current = moveVertex(latest.current ?? [], active.index, [
        at.x - options.origin.x,
        at.y - options.origin.y,
      ]);
      setPreview(latest.current);
    };
    const onUp = () => {
      const active = grabbed.current;
      const moved = latest.current;
      grabbed.current = null;
      setPreview(null);
      // A click on a corner is not an edit, and saving one still costs a
      // recomputation of every bed's light.
      if (active === null || !active.moved || moved === null) return;
      options.onFinish(moved);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [preview, options]);

  return { preview, grab };
}
