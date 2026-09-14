import { type KeyboardEvent, type ReactNode, useId, useLayoutEffect, useRef } from 'react';

import { isTextEntry } from '../canvas/useEscapeKey';
import { SNAP_FRACTION, type Snap } from '../workspace/sheet';
import { useInertOutside } from '../workspace/useInertOutside';
import { SheetHandle } from './SheetHandle';

/** The details as a sheet from below, on a narrow window (doc 91). */
export interface SheetControl {
  snap: Snap;
  onSnap: (snap: Snap) => void;
  /** A drag in progress, as the share of the space the sheet has reached; null once it ends. */
  onDrag: (fraction: number | null) => void;
}

interface Props {
  wide: boolean;
  onWide: (wide: boolean) => void;
  /** Given on a narrow window, where the details are a sheet from below. */
  sheet?: SheetControl | undefined;
  children: ReactNode;
}

/**
 * The details beside the plan: its own scroll, and one of two widths (doc 87).
 *
 * Two widths rather than a drag handle. The range the plan asked for is too
 * narrow to be worth a gesture, and a toggle is one keyboard stop whose state a
 * screen reader can name. The button keeps its name in both states and
 * `aria-pressed` carries the state, so the state is never said twice.
 *
 * On a narrow window the same details are a sheet from below (doc 91): a handle
 * first, and at 90 % the rest of the page inert and Escape the way back down.
 */
export function Inspector({ wide, onWide, sheet, children }: Props) {
  const id = useId();
  const aside = useRef<HTMLElement>(null);
  const trapped = sheet?.snap === 'full';
  useInertOutside(aside, trapped);

  // Risen to 90 % while the focus was outside: the focus follows it in.
  useLayoutEffect(() => {
    const element = aside.current;
    if (!trapped || element === null || element.contains(document.activeElement)) return;
    element.querySelector<HTMLElement>('.sheet-handle')?.focus();
  }, [trapped]);

  // Escape leaves the trap. It stops here, so the plan's Escape, which clears
  // the selection (doc 88), never hears it; typed into a field it is the field's.
  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (!trapped || event.key !== 'Escape' || isTextEntry(event.target)) return;
    event.preventDefault();
    event.stopPropagation();
    sheet?.onSnap('half');
  };

  return (
    <aside
      id={id}
      ref={aside}
      className="inspector"
      aria-label="Details"
      data-snap={sheet?.snap}
      onKeyDown={sheet !== undefined ? onKeyDown : undefined}
    >
      {sheet !== undefined ? (
        <SheetHandle
          snap={sheet.snap}
          onSnap={sheet.onSnap}
          onDrag={sheet.onDrag}
          controls={id}
          space={() => (aside.current?.clientHeight ?? 0) / SNAP_FRACTION[sheet.snap]}
        />
      ) : null}
      <div className="inspector__bar">
        <button
          type="button"
          className="link-button inspector__width"
          aria-pressed={wide}
          onClick={() => onWide(!wide)}
        >
          Breite Ansicht
        </button>
      </div>
      {children}
    </aside>
  );
}
