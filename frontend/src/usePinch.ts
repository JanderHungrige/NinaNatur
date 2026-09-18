import { type PointerEvent as ReactPointerEvent, useRef } from 'react';

export interface PinchChange {
  /** How much further apart the fingers are than at the last change; above 1 is a spread. */
  scale: number;
  /** The point between them, in the surface's own pixels. */
  at: { x: number; y: number };
  /** How far that point has moved since the last change, in pixels. */
  moved: { x: number; y: number };
}

interface Options {
  /** A second finger landed: whatever the first one was doing is over. */
  onStart: () => void;
  onChange: (change: PinchChange) => void;
}

type Handler = (event: ReactPointerEvent<Element>) => void;

interface Pinch {
  onPointerDownCapture: Handler;
  onPointerMoveCapture: Handler;
  onPointerUpCapture: Handler;
  onPointerCancelCapture: Handler;
}

/**
 * Two fingers on one surface (doc 91, B1 for the plan; doc 31, B2 for the map).
 *
 * Both surfaces set `touch-action: none`, so that one finger drags them rather
 * than the page — which switches the browser's own pinch off as well. This is
 * what replaces it. Its handlers belong on the surface's capture phase: it sees
 * every finger before a shape under one does, and while two are down it keeps
 * their moves from the pan and the drags beneath.
 */
export function usePinch({ onStart, onChange }: Options): Pinch {
  const fingers = useRef(new Map<number, { x: number; y: number }>());
  const last = useRef<{ spread: number; middle: { x: number; y: number } } | null>(null);

  /** The first two fingers down: how far apart, and the point between them. */
  const pair = () => {
    const [a, b] = [...fingers.current.values()];
    if (a === undefined || b === undefined) return null;
    return {
      spread: Math.hypot(a.x - b.x, a.y - b.y),
      middle: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 },
    };
  };

  const onPointerDownCapture: Handler = (event) => {
    if (event.pointerType !== 'touch') return;
    fingers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (fingers.current.size !== 2) return;
    last.current = pair();
    onStart();
    // Not also the start of a drag of whatever lies under the second finger.
    event.stopPropagation();
  };

  const onPointerMoveCapture: Handler = (event) => {
    if (!fingers.current.has(event.pointerId)) return;
    fingers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const was = last.current;
    const now = pair();
    if (was === null || now === null) return;
    event.stopPropagation();
    if (was.spread === 0) return;
    const box = event.currentTarget.getBoundingClientRect();
    onChange({
      scale: now.spread / was.spread,
      at: { x: now.middle.x - box.left, y: now.middle.y - box.top },
      moved: { x: now.middle.x - was.middle.x, y: now.middle.y - was.middle.y },
    });
    last.current = now;
  };

  const onPointerUpCapture: Handler = (event) => {
    if (!fingers.current.delete(event.pointerId)) return;
    // One finger left of two is no pan either: it waits to be lifted.
    if (fingers.current.size < 2) last.current = null;
  };

  return {
    onPointerDownCapture,
    onPointerMoveCapture,
    onPointerUpCapture,
    onPointerCancelCapture: onPointerUpCapture,
  };
}
