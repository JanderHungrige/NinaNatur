/**
 * Dragging a resize or rotation handle.
 *
 * Lifted out of GardenCanvas when that component passed 400 lines carrying five
 * interaction modes at once. This is the one with arithmetic in it; the rest of
 * what was there is bookkeeping.
 */
import { useEffect, useRef, useState } from 'react';

import { type Box, type Handle, resizeBy, rotateBy } from './handles';
import { type Viewport, toGarden } from './viewport';

interface Options {
  selectedBox: Box | null;
  /** Round shapes resize square: a pond has a diameter, not a width and a depth. */
  keepSquare: boolean;
  view: Viewport;
  surface: React.RefObject<SVGSVGElement | null>;
  onFinish: (box: Box) => void;
}

export function useHandleDrag(options: Options): {
  preview: Box | null;
  grabHandle: (handle: Handle | 'rotate', event: React.PointerEvent) => void;
} {
  const perPixel = options.view.spanM / options.view.widthPx;
  const [preview, setPreview] = useState<Box | null>(null);
  const grab = useRef<{
    handle: Handle | 'rotate';
    startPx: { x: number; y: number };
    box: Box;
    moved: boolean;
  } | null>(null);

  const grabHandle = (handle: Handle | 'rotate', event: React.PointerEvent) => {
    if (options.selectedBox === null) return;
    // The surface below would otherwise read this as a click on the plan, and
    // grabbing a handle would drop a bed corner or place a second house.
    event.stopPropagation();
    grab.current = {
      handle,
      startPx: { x: event.clientX, y: event.clientY },
      box: options.selectedBox,
      moved: false,
    };
    setPreview(options.selectedBox);
  };

  /**
   * The drag itself, on the window rather than on the handle: a pointer that
   * leaves the little square mid-gesture must keep resizing, which is what
   * makes a handle feel like a handle.
   */
  useEffect(() => {
    if (preview === null) return undefined;
    const onMove = (event: PointerEvent) => {
      const active = grab.current;
      if (active === null) return;
      const dxPx = event.clientX - active.startPx.x;
      const dyPx = event.clientY - active.startPx.y;
      if (dxPx !== 0 || dyPx !== 0) active.moved = true;

      if (active.handle === 'rotate') {
        const rect = options.surface.current?.getBoundingClientRect();
        const pointer = toGarden(
          { x: event.clientX - (rect?.left ?? 0), y: event.clientY - (rect?.top ?? 0) },
          options.view,
        );
        setPreview({
          ...active.box,
          rotation: rotateBy(active.box, pointer, { free: event.altKey }),
        });
        return;
      }
      // Screen y grows downward, garden y grows north.
      setPreview(
        resizeBy(
          active.box,
          active.handle,
          { dx: dxPx * perPixel, dy: -dyPx * perPixel },
          { keepSquare: options.keepSquare },
        ),
      );
    };
    const onUp = () => {
      const active = grab.current;
      grab.current = null;
      const shape = preview;
      setPreview(null);
      // Clicking a handle is not a resize. Saving one anyway costs a PATCH and
      // a recomputation of every bed's light for a gesture that changed nothing.
      if (active === null || !active.moved || shape === null) return;
      options.onFinish(shape);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [preview, perPixel, options]);

  return { preview, grabHandle };
}
