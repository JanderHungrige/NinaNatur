/**
 * Moving an element by dragging its body.
 *
 * The half that was missing: handles resized a shape and dragging it panned the
 * plan, which looks exactly like the shape moving while nothing about the
 * garden has changed. Grabbing a shape now moves it; grabbing empty ground
 * still pans.
 */
import { useEffect, useRef, useState } from 'react';

import { type Point, type Viewport, toGarden } from './viewport';

interface Options {
  view: Viewport;
  surface: React.RefObject<SVGSVGElement | null>;
  onFinish: (id: number, at: Point) => void;
}

export function useElementDrag(options: Options) {
  /** Where the shape is being shown while the pointer holds it. */
  const [offset, setOffset] = useState<{ id: number; dx: number; dy: number } | null>(null);
  const held = useRef<{ id: number; from: Point; moved: boolean } | null>(null);
  const latest = useRef<{ dx: number; dy: number }>({ dx: 0, dy: 0 });

  const metres = (event: { clientX: number; clientY: number }): Point => {
    const rect = options.surface.current?.getBoundingClientRect();
    return toGarden(
      { x: event.clientX - (rect?.left ?? 0), y: event.clientY - (rect?.top ?? 0) },
      options.view,
    );
  };

  const grab = (id: number, event: React.PointerEvent) => {
    // The surface below would otherwise read this as the start of a pan.
    event.stopPropagation();
    held.current = { id, from: metres(event), moved: false };
    latest.current = { dx: 0, dy: 0 };
    setOffset({ id, dx: 0, dy: 0 });
  };

  useEffect(() => {
    if (offset === null) return undefined;
    const onMove = (event: PointerEvent) => {
      const active = held.current;
      if (active === null) return;
      const at = metres(event);
      latest.current = { dx: at.x - active.from.x, dy: at.y - active.from.y };
      if (latest.current.dx !== 0 || latest.current.dy !== 0) active.moved = true;
      setOffset({ id: active.id, ...latest.current });
    };
    const onUp = () => {
      const active = held.current;
      held.current = null;
      setOffset(null);
      // A click on a shape selects it. Saving a move of nothing still costs a
      // PATCH and a recomputation of every bed's light.
      if (active === null || !active.moved) return;
      options.onFinish(active.id, {
        x: Math.round(latest.current.dx * 100) / 100,
        y: Math.round(latest.current.dy * 100) / 100,
      });
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [offset, options]);

  return { offset, grab };
}
