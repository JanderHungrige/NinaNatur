/**
 * Moving an element by dragging its body.
 *
 * The half that was missing: handles resized a shape and dragging it panned the
 * plan, which looks exactly like the shape moving while nothing about the
 * garden has changed. Grabbing a shape now moves it; grabbing empty ground
 * still pans.
 *
 * Which pointer may pick up which element is the caller's to say (doc 87, B1).
 * A grab it refuses is left to the surface beneath, which pans.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { type Point, type Viewport, toGarden } from './viewport';

interface Options {
  view: Viewport;
  surface: React.RefObject<SVGSVGElement | null>;
  /** Whether this pointer may pick this element up; `byFinger` is a touch. */
  movable: (id: number, byFinger: boolean) => boolean;
  onFinish: (id: number, at: Point) => void;
}

export function useElementDrag(options: Options) {
  /** Where the shape is being shown while the pointer holds it. */
  const [offset, setOffset] = useState<{ id: number; dx: number; dy: number } | null>(null);
  const held = useRef<{ id: number; from: Point; moved: boolean } | null>(null);
  const latest = useRef<{ dx: number; dy: number }>({ dx: 0, dy: 0 });
  // Read through a ref: `options` is a new object on every render, and as an
  // effect dependency it tore the window listeners down and put them back on
  // every pointer move of every drag (the owner's check, #11). It also keeps
  // `grab` one function for the life of the plan, which the memoised scene needs.
  const current = useRef(options);
  current.current = options;

  const metres = useCallback((event: { clientX: number; clientY: number }): Point => {
    const rect = current.current.surface.current?.getBoundingClientRect();
    return toGarden(
      { x: event.clientX - (rect?.left ?? 0), y: event.clientY - (rect?.top ?? 0) },
      current.current.view,
    );
  }, []);

  const grab = useCallback((id: number, event: React.PointerEvent) => {
    // `touch` only: a pen is as exact as a mouse, and jsdom reports a pointer
    // whose type was never set as ''.
    if (!current.current.movable(id, event.pointerType === 'touch')) return;
    // The surface below would otherwise read this as the start of a pan.
    event.stopPropagation();
    held.current = { id, from: metres(event), moved: false };
    latest.current = { dx: 0, dy: 0 };
    setOffset({ id, dx: 0, dy: 0 });
  }, [metres]);

  /** Ended by a second finger (doc 91, B1): nothing moved, and nothing is saved. */
  const cancel = () => {
    held.current = null;
    setOffset(null);
  };

  const holding = offset !== null;
  useEffect(() => {
    if (!holding) return undefined;
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
      current.current.onFinish(active.id, {
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
  }, [holding, metres]);

  return { offset, grab, cancel };
}
