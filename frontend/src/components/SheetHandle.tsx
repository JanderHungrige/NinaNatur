import { type KeyboardEvent, type PointerEvent, useRef } from 'react';

import {
  SNAP_FRACTION,
  SNAP_WORDS,
  type Snap,
  dragFraction,
  lowered,
  raised,
  restingSnap,
} from '../workspace/sheet';

interface Props {
  snap: Snap;
  onSnap: (snap: Snap) => void;
  /** A drag in progress, as the share of the space it has reached; null once it ends. */
  onDrag: (fraction: number | null) => void;
  /** The id of the details this handle sizes. */
  controls: string;
  /** How many pixels the heights are shares of, measured as a drag starts. */
  space: () => number;
  /** The clock a flick is timed by: the page's, unless a test brings its own. */
  now?: () => number;
}

/** A finger that travels no further than this is a tap. */
const TAP_PX = 6;
/** How far back a flick's speed is measured from. */
const FLICK_WINDOW_MS = 80;

interface Drag {
  startY: number;
  start: number;
  space: number;
  moved: boolean;
  samples: Array<{ y: number; t: number }>;
}

/** Enter's height: a quarter and 60 % in turn, and down to 60 % from 90 %. */
const toggled = (snap: Snap): Snap => (snap === 'half' ? 'peek' : 'half');

const KEYS: Readonly<Record<string, (snap: Snap) => Snap>> = {
  ArrowUp: raised,
  PageUp: raised,
  ArrowDown: lowered,
  PageDown: lowered,
  Home: () => 'peek',
  End: () => 'full',
  Enter: toggled,
};

/**
 * The sheet's handle (doc 91): a window splitter for the keyboard and a screen
 * reader, a drag and a flick for a finger. It says where the sheet should
 * stand; the workspace moves it.
 */
export function SheetHandle({ snap, onSnap, onDrag, controls, space, now = () => performance.now() }: Props) {
  const drag = useRef<Drag | null>(null);

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const next = KEYS[event.key];
    if (next === undefined) return;
    event.preventDefault();
    onSnap(next(snap));
  };

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    drag.current = {
      startY: event.clientY,
      start: SNAP_FRACTION[snap],
      space: space(),
      moved: false,
      samples: [{ y: event.clientY, t: now() }],
    };
  };

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const current = drag.current;
    if (current === null) return;
    if (Math.abs(event.clientY - current.startY) > TAP_PX) current.moved = true;
    current.samples = [...current.samples.slice(-4), { y: event.clientY, t: now() }];
    if (current.moved) onDrag(dragFraction(current.start, current.startY, event.clientY, current.space));
  };

  const onPointerUp = (event: PointerEvent<HTMLDivElement>) => {
    const current = drag.current;
    if (current === null) return;
    drag.current = null;
    onDrag(null);
    if (!current.moved && Math.abs(event.clientY - current.startY) <= TAP_PX) {
      onSnap(toggled(snap));
      return;
    }
    const t = now();
    const from = [...current.samples].reverse().find((sample) => t - sample.t >= FLICK_WINDOW_MS) ??
      current.samples[0] ?? { y: current.startY, t };
    const perSecond = ((from.y - event.clientY) / Math.max(t - from.t, 16)) * 1000;
    const velocity = current.space > 0 ? perSecond / current.space : 0;
    onSnap(restingSnap(dragFraction(current.start, current.startY, event.clientY, current.space), velocity));
  };

  const onPointerCancel = () => {
    if (drag.current === null) return;
    drag.current = null;
    onDrag(null);
  };

  return (
    <div
      role="separator"
      tabIndex={0}
      className="sheet-handle"
      aria-orientation="horizontal"
      aria-label="Höhe der Details"
      aria-controls={controls}
      aria-valuemin={25}
      aria-valuemax={90}
      aria-valuenow={Math.round(SNAP_FRACTION[snap] * 100)}
      aria-valuetext={SNAP_WORDS[snap]}
      onKeyDown={onKeyDown}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerCancel}
    >
      <span className="sheet-handle__grip" aria-hidden="true" />
    </div>
  );
}
