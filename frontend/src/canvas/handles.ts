/**
 * Resize and rotate handles, in the manner of draw.io.
 *
 * All of this works in garden metres, in the object's own frame. A handle drag
 * measured in screen pixels would resize differently at every zoom level, which
 * is the same mistake snapping already avoids.
 */
import type { Point } from './viewport';

export interface Box {
  x: number;
  y: number;
  width: number;
  depth: number;
  /** Degrees clockwise from north, like the compass and the solar azimuth. */
  rotation: number;
}

/** The eight of draw.io. Fewer and a user cannot pull one side; more and they
 *  cannot hit any of them. */
export const HANDLES = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'] as const;
export type Handle = (typeof HANDLES)[number];

/** Below this a shape is a mis-drag rather than a request for a small one. */
const MIN_SIDE_M = 0.2;
const ROTATION_STEP_DEG = 15;

/** Unit offsets in the object's own frame: +1 east, +1 north. */
const OFFSET: Record<Handle, [number, number]> = {
  n: [0, 1],
  ne: [1, 1],
  e: [1, 0],
  se: [1, -1],
  s: [0, -1],
  sw: [-1, -1],
  w: [-1, 0],
  nw: [-1, 1],
};

function rotate(px: number, py: number, degrees: number): Point {
  const a = (degrees * Math.PI) / 180;
  const cos = Math.cos(a);
  const sin = Math.sin(a);
  return { x: px * cos + py * sin, y: -px * sin + py * cos };
}

function unrotate(px: number, py: number, degrees: number): Point {
  return rotate(px, py, -degrees);
}

/** Where a handle sits, in garden metres. */
export function handleAt(box: Box, handle: Handle): Point {
  const [ox, oy] = OFFSET[handle];
  const local = rotate((ox * box.width) / 2, (oy * box.depth) / 2, box.rotation);
  return { x: box.x + local.x, y: box.y + local.y };
}

/**
 * Resize by a pointer movement, keeping the opposite edge still.
 *
 * The delta is turned into the object's own frame first: on a house turned 90°,
 * pulling its east handle must widen it along its own axis, not along the
 * screen's. Without that, rotating an object makes its handles lie.
 */
export function resizeBy(
  box: Box,
  handle: Handle,
  delta: { dx: number; dy: number },
  options: { keepSquare?: boolean } = {},
): Box {
  const [ox, oy] = OFFSET[handle];
  const local = unrotate(delta.dx, delta.dy, box.rotation);

  let width = Math.max(MIN_SIDE_M, box.width + ox * local.x);
  let depth = Math.max(MIN_SIDE_M, box.depth + oy * local.y);
  // A tree or a pond is a diameter, not a width and a depth. Letting the two
  // diverge draws a preview rectangle over a shape the server will return as a
  // circle — the drag would show the user something that cannot happen.
  if (options.keepSquare === true) {
    const side = Math.max(width, depth);
    width = side;
    depth = side;
  }

  // The centre moves by half of what the edge did, so the far edge stays put.
  const shift = rotate((ox * (width - box.width)) / 2, (oy * (depth - box.depth)) / 2,
    box.rotation);
  return { ...box, width, depth, x: box.x + shift.x, y: box.y + shift.y };
}

/**
 * The rotation that points the object at `pointer`, in degrees clockwise from
 * north. Snapped to 15° so a house ends up square with the fence unless the
 * user says otherwise.
 */
export function rotateBy(box: Box, pointer: Point, options: { free?: boolean } = {}): number {
  const dx = pointer.x - box.x;
  const dy = pointer.y - box.y;
  const degrees = (Math.atan2(dx, dy) * 180) / Math.PI;
  const wrapped = ((degrees % 360) + 360) % 360;
  return options.free === true
    ? wrapped
    : Math.round(wrapped / ROTATION_STEP_DEG) * ROTATION_STEP_DEG;
}

/** What the canvas needs to know about an element to put handles on it. */
export interface Geometry {
  shape: string;
  x: number;
  y: number;
  width: number | null;
  constraint_hint: string | null;
  points: number[][] | null;
  footprint: number[][];
}

/**
 * The editing box for an element.
 *
 * Wave 11 stores points rather than a width, a depth and an angle, so dragging
 * a vertex has nothing to convert. The handles still work in a box, so it is
 * derived here — and the derivation has to survive a round trip, or selecting a
 * shape would nudge it every time.
 *
 * A rectangle's corners are stored in a known order, so its own axes can be
 * read straight off the first two edges. Anything else falls back to its
 * bounding box: a freehand outline has no width and no angle to recover, and
 * pretending otherwise would put the handles somewhere the user did not draw.
 */
export function boxOf(element: Geometry): Box {
  if (element.shape === 'circle') {
    const diameter = element.width ?? 0;
    return { x: element.x, y: element.y, width: diameter, depth: diameter, rotation: 0 };
  }

  const points = element.points ?? element.footprint.map((p) => [p[0]! - element.x, p[1]! - element.y]);
  const RECT_CORNERS = 4;
  if (element.constraint_hint === 'rect' && points.length === RECT_CORNERS) {
    const [a, b, c] = points as [number[], number[], number[]];
    const ex = b[0]! - a[0]!;
    const ey = b[1]! - a[1]!;
    return {
      x: element.x,
      y: element.y,
      width: Math.hypot(ex, ey),
      depth: Math.hypot(c[0]! - b[0]!, c[1]! - b[1]!),
      // Clockwise from north, matching the compass and the solar azimuth.
      rotation: (Math.atan2(-ey, ex) * 180) / Math.PI,
    };
  }

  const xs = points.map((p) => p[0]!);
  const ys = points.map((p) => p[1]!);
  return {
    x: element.x,
    y: element.y,
    width: Math.max(...xs) - Math.min(...xs),
    depth: Math.max(...ys) - Math.min(...ys),
    rotation: 0,
  };
}
