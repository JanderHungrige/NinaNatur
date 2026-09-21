import { type RefObject, forwardRef, useImperativeHandle } from 'react';

import type { LightMap } from '../api/client';
import { useSunReadout } from '../canvas/useSunReadout';
import type { Viewport } from '../canvas/viewport';

export interface SunReadoutHandle {
  read: (event: { clientX: number; clientY: number }) => void;
  clear: () => void;
}

interface Props {
  map: LightMap | undefined;
  view: Viewport;
  surface: RefObject<SVGSVGElement | null>;
}

/**
 * What the sun map says under the pointer, as its own small component.
 *
 * Its state used to live in the plan. Every mouse move over the plan with the
 * shade on then re-rendered the whole scene, thousands of cells included, only
 * to move one label (the owner's check, 2026-09-21, #11). Here a move
 * re-renders this, and nothing else.
 */
export const SunReadout = forwardRef<SunReadoutHandle, Props>(function SunReadout(
  { map, view, surface },
  ref,
) {
  const sun = useSunReadout(map, view, surface);
  useImperativeHandle(ref, () => ({ read: sun.read, clear: sun.clear }), [sun.read, sun.clear]);
  if (sun.readout === null) return null;
  return (
    <div
      className="sun-readout"
      data-testid="sun-readout"
      style={{ left: sun.readout.left, top: sun.readout.top }}
    >
      {sun.readout.text}
    </div>
  );
});
