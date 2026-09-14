/**
 * The one place screen pixels become metres, and metres become pixels.
 *
 * Written as pure functions over an explicit viewport rather than as a hook,
 * because every one of these rules is a fact about arithmetic that a test should
 * be able to state without rendering anything. A second conversion written
 * inline somewhere is a second answer, and the two will disagree the first time
 * someone zooms.
 */

export interface Point {
  x: number;
  y: number;
}

/** What part of the garden is on screen, and how big the screen is. */
export interface Viewport {
  /** Garden metres at the centre of the window. */
  centreX: number;
  centreY: number;
  /** How many metres the *width* of the window covers. */
  spanM: number;
  widthPx: number;
  heightPx: number;
}

// Clamped where the grid can still be honest: below 2 m a metre is the whole
// window, above 1,000 m even a 100 m grid is a wash.
export const MIN_SPAN_M = 2;
export const MAX_SPAN_M = 1000;

/** Spacings a person reads without converting. */
const SPACINGS = [1, 5, 25, 100] as const;

/** Below this a grid line is texture, not a measurement. */
const MIN_LINE_GAP_PX = 6;

function pixelsPerMetre(view: Viewport): number {
  return view.widthPx / view.spanM;
}

export function toScreen(point: Point, view: Viewport): Point {
  const scale = pixelsPerMetre(view);
  return {
    x: view.widthPx / 2 + (point.x - view.centreX) * scale,
    // Garden y grows north, screen y grows down. Getting this backwards mirrors
    // every shadow the solar model computes.
    y: view.heightPx / 2 - (point.y - view.centreY) * scale,
  };
}

export function toGarden(point: Point, view: Viewport): Point {
  const scale = pixelsPerMetre(view);
  return {
    x: view.centreX + (point.x - view.widthPx / 2) / scale,
    y: view.centreY - (point.y - view.heightPx / 2) / scale,
  };
}

/**
 * Zoom by `factor`, keeping the metre under `pointer` under `pointer`.
 *
 * Anchoring on the centre instead makes the user chase their own garden across
 * the screen with every scroll.
 */
export function zoomAt(view: Viewport, pointer: Point, factor: number): Viewport {
  const spanM = Math.min(MAX_SPAN_M, Math.max(MIN_SPAN_M, view.spanM * factor));
  if (spanM === view.spanM) return view;

  const anchor = toGarden(pointer, view);
  const zoomed: Viewport = { ...view, spanM };
  const drifted = toGarden(pointer, zoomed);
  return {
    ...zoomed,
    centreX: zoomed.centreX + (anchor.x - drifted.x),
    centreY: zoomed.centreY + (anchor.y - drifted.y),
  };
}

/** Pan by a screen-pixel delta. */
export function panBy(view: Viewport, dxPx: number, dyPx: number): Viewport {
  const scale = pixelsPerMetre(view);
  return { ...view, centreX: view.centreX - dxPx / scale, centreY: view.centreY + dyPx / scale };
}

/**
 * The grid spacing that is currently truthful, in metres.
 *
 * A grid that keeps drawing every metre once metres are two pixels apart is not
 * a grid, it is a fill — and it still says "1 m", which makes it a measurement
 * that is wrong.
 */
export function gridSpacing(view: Viewport): number {
  const scale = pixelsPerMetre(view);
  for (const spacing of SPACINGS) {
    if (spacing * scale >= MIN_LINE_GAP_PX) return spacing;
  }
  return SPACINGS[SPACINGS.length - 1] as number;
}

/** A box as `getBoundingClientRect` measures it. */
export interface Measured {
  width: number;
  height: number;
}

/** The shape of a window nothing has measured yet: the old 800×600. */
const UNMEASURED_SHAPE = 0.75;

const isSize = (value: number): boolean => Number.isFinite(value) && value > 0;

/**
 * The view with a measured size in it, or the view unchanged when the
 * measurement is not one.
 *
 * A box that has not been laid out — a background tab, a hidden panel — measures
 * zero, and taking that as a size is how one bad frame used to become the plan's
 * shape until the next reload. A real measurement is taken exactly, however
 * short and wide: a view shaped unlike its box would letterbox the drawing and
 * move every click off the metre it points at. An unchanged size hands back the
 * same view, so React has nothing to redraw.
 */
export function measuredView(view: Viewport, box: Measured): Viewport {
  if (!isSize(box.width) || !isSize(box.height)) return view;
  if (box.width === view.widthPx && box.height === view.heightPx) return view;
  return { ...view, widthPx: box.width, heightPx: box.height };
}

/**
 * The SVG viewBox for this window, in garden metres with y already flipped.
 *
 * Exactly the shape of the stored size, so the drawing fills its box. Only a
 * size that is not one falls back to 3:4: a viewBox with no height draws nothing,
 * and one with no width divides by zero.
 */
export function viewBox(view: Viewport): string {
  const shape =
    isSize(view.widthPx) && isSize(view.heightPx) ? view.heightPx / view.widthPx : UNMEASURED_SHAPE;
  const heightM = view.spanM * shape;
  const minX = view.centreX - view.spanM / 2;
  // SVG y grows down, so the top edge is the *northern* one negated.
  const minY = -(view.centreY + heightM / 2);
  return `${minX} ${minY} ${view.spanM} ${heightM}`;
}
