import { useEffect, useLayoutEffect, useRef, useState } from 'react';

/** Space kept between the menu and the edge of the window, in pixels. */
const MARGIN = 8;
/** How far the menu sits from the shape it belongs to. */
const GAP = 6;

export interface Placement {
  left: number;
  top: number;
}

/**
 * Where a menu about one shape should sit.
 *
 * Two things went wrong before, and they look like one complaint. The menu was
 * `position: fixed` at the click's viewport coordinate, with nothing clamping
 * it — so a right-click near the bottom of the window put half of it below the
 * fold. And because `fixed` ignores scrolling, scrolling could not bring that
 * half back: the page moved, the shape moved, the menu stayed exactly where it
 * was.
 *
 * So it anchors to the shape's own box, re-measured whenever the page scrolls
 * or the window resizes, and it is placed where it fits: below the shape by
 * preference, above it when there is no room below, and clamped to the window
 * as the last resort. The click point is only the fallback for a shape that is
 * no longer in the document.
 */
export function useAnchoredMenu(
  elementId: number,
  fallback: { x: number; y: number },
): { ref: React.RefObject<HTMLDivElement>; placement: Placement } {
  const ref = useRef<HTMLDivElement>(null) as React.RefObject<HTMLDivElement>;
  const [placement, setPlacement] = useState<Placement>({
    left: fallback.x,
    top: fallback.y,
  });

  // Layout effect, not effect: the first paint should already be in the right
  // place. An effect here shows the menu at the fallback for one frame, which
  // reads as a jump.
  useLayoutEffect(() => {
    const place = () => {
      const menu = ref.current;
      if (menu === null) return;
      const anchor = document
        .querySelector(`[data-element-id="${elementId}"]`)
        ?.getBoundingClientRect();
      setPlacement(
        fit(
          anchor ?? { left: fallback.x, top: fallback.y, bottom: fallback.y, right: fallback.x },
          menu.getBoundingClientRect(),
        ),
      );
    };
    place();

    // Capture phase: the plan scrolls inside its own column on a narrow window,
    // and a listener on `window` alone never hears that one.
    window.addEventListener('scroll', place, true);
    window.addEventListener('resize', place);
    return () => {
      window.removeEventListener('scroll', place, true);
      window.removeEventListener('resize', place);
    };
  }, [elementId, fallback.x, fallback.y]);

  // The menu changes height as the kind changes — a line gains a width field —
  // and a menu that was placed above a shape must be placed again when it does.
  useEffect(() => {
    const menu = ref.current;
    if (menu === null || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => {
      const anchor = document
        .querySelector(`[data-element-id="${elementId}"]`)
        ?.getBoundingClientRect();
      if (anchor === undefined) return;
      setPlacement(fit(anchor, menu.getBoundingClientRect()));
    });
    observer.observe(menu);
    return () => observer.disconnect();
  }, [elementId]);

  return { ref, placement };
}

/** Below the anchor if it fits, above it if not, inside the window regardless. */
export function fit(
  anchor: { left: number; top: number; bottom: number; right: number },
  menu: { width: number; height: number },
  view: { width: number; height: number } = {
    width: window.innerWidth,
    height: window.innerHeight,
  },
): Placement {
  const below = anchor.bottom + GAP;
  const above = anchor.top - menu.height - GAP;
  // Below by preference: it is where a menu is expected, and it does not cover
  // the thing it is about.
  const top =
    below + menu.height <= view.height - MARGIN
      ? below
      : above >= MARGIN
        ? above
        : clamp(below, MARGIN, view.height - menu.height - MARGIN);

  const left = clamp(anchor.left, MARGIN, view.width - menu.width - MARGIN);
  return { left, top };
}

function clamp(value: number, low: number, high: number): number {
  // A menu taller than the window makes `high` smaller than `low`. Pinning to
  // the top is then the only useful answer: the head of a menu is where its
  // heading and its close button are.
  return high < low ? low : Math.min(Math.max(value, low), high);
}
