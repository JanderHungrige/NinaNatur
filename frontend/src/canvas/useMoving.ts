/**
 * Whether the plan is being moved: panned, pinched or wheeled.
 *
 * While it moves, the costliest paint pauses. That is Technisch's watercolour
 * filter over every shape, and Draft Sketch's paper and bloom masks (the
 * stylesheets' `.canvas--moving` rules). A viewBox change repaints the whole
 * drawing on every frame, and those layers were most of what a frame cost:
 * 66–98 ms per zoom step on a phone (the owner's check, 2026-09-21, #11). The
 * class goes straight onto the element. A state change would re-render the
 * very scene it exists to spare.
 */
import { type RefObject, useEffect, useMemo, useRef } from 'react';

export const MOVING = 'canvas--moving';

/** How long after the last wheel event the plan counts as still. */
const IDLE_MS = 150;

export interface Moving {
  /** A gesture began: a pan's first move, a pinch's second finger. */
  start: () => void;
  /** It ended. */
  stop: () => void;
  /** One event of a gesture that has no end of its own: the wheel. */
  pulse: () => void;
}

export function useMoving(surface: RefObject<Element | null>): Moving {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const moving = useMemo<Moving>(() => {
    const forget = () => {
      if (timer.current !== null) clearTimeout(timer.current);
      timer.current = null;
    };
    const start = () => {
      forget();
      surface.current?.classList.add(MOVING);
    };
    const stop = () => {
      forget();
      surface.current?.classList.remove(MOVING);
    };
    return {
      start,
      stop,
      pulse: () => {
        start();
        timer.current = setTimeout(stop, IDLE_MS);
      },
    };
  }, [surface]);
  useEffect(() => () => moving.stop(), [moving]);
  return moving;
}
