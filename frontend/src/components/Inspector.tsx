import type { ReactNode } from 'react';

interface Props {
  wide: boolean;
  onWide: (wide: boolean) => void;
  children: ReactNode;
}

/**
 * The details beside the plan: its own scroll, and one of two widths (doc 87).
 *
 * Two widths rather than a drag handle. The range the plan asked for is too
 * narrow to be worth a gesture, and a toggle is one keyboard stop whose state a
 * screen reader can name. The button keeps its name in both states and
 * `aria-pressed` carries the state, so the state is never said twice.
 */
export function Inspector({ wide, onWide, children }: Props) {
  return (
    <aside className="inspector" aria-label="Details">
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
