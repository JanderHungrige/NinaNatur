import { useEffect, useId, useRef } from 'react';

import type { ShadowMark } from '../api/client';
import { nowLocal, readingWords, seenWords } from '../shadowMarks';
import { focusLost, holdsFocus } from '../suggestions/focus';

interface Props {
  /** The standing thing whose shadow is marked. */
  elementId: number;
  /** Whether it casts a shadow to mark now. A thing that stopped casting keeps
   *  its marks listed, so they can be forgotten. */
  canMark: boolean;
  /** Every mark of the garden's; the panel shows this element's. */
  marks: ShadowMark[];
  /** The moment the gardener typed, as a `datetime-local` value; null is now. */
  seenAt: string | null;
  onSeenAt: (value: string) => void;
  /** Whether the plan's next click marks this element's shadow. */
  armed: boolean;
  /** Arms the plan, or puts the mark down again while armed. */
  onToggle: () => void;
  onRemove: (markId: number) => void;
  busy: boolean;
}

/**
 * Where the gardener saw this thing's shadow end, against the model (doc 122).
 *
 * The one instrument in the page that reaches the real garden: a wrong height,
 * a plan turned on its north or a garden put in the next street all show as a
 * shadow edge somewhere other than where somebody standing there sees it. The
 * reading is said, never applied: the height and the plan stay the gardener's
 * to correct, where they already can.
 *
 * Nothing is disabled while a request runs — the buttons are `aria-disabled`
 * and ignore presses instead, as the element form's are (doc 87). A mark
 * forgotten takes its button with it; the focus then goes to the heading
 * rather than falling to the page (doc 90).
 */
export function ShadowMarkPanel({
  elementId, canMark, marks, seenAt, onSeenAt, armed, onToggle, onRemove, busy,
}: Props) {
  const id = useId();
  const box = useRef<HTMLElement | null>(null);
  const heading = useRef<HTMLHeadingElement | null>(null);
  const mine = marks.filter((mark) => mark.element_id === elementId);
  // Read while rendering, before a commit removes the button holding it.
  const holding = useRef(false);
  holding.current = holdsFocus(box.current);
  useEffect(() => {
    if (holding.current && focusLost()) heading.current?.focus();
  }, [mine.length]);
  const unlessBusy = (action: () => void) => () => {
    if (!busy) action();
  };

  return (
    <section ref={box} className="panel shadow-mark-panel" aria-labelledby={`${id}-heading`}>
      <h2 id={`${id}-heading`} ref={heading} tabIndex={-1}>Schattenkante</h2>
      {canMark && (
        <>
          <p className="hint">
            Wo endet sein Schatten gerade? Markiere die Kante im Plan, und das Modell sagt, wie
            weit es danebenliegt — so zeigt sich eine falsche Höhe, eine verdrehte Nordrichtung
            oder ein falscher Standort.
          </p>
          <label htmlFor={`${id}-seen`}>Gesehen am</label>
          <input id={`${id}-seen`} type="datetime-local" value={seenAt ?? nowLocal()}
                 onChange={(e) => onSeenAt(e.target.value)}
                 aria-describedby={`${id}-seen-said`} />
          <p id={`${id}-seen-said`} className="hint">
            {seenAt === null ? 'Jetzt — der Moment des Klicks.' : 'Leeren für jetzt.'}
          </p>
          <button type="button" aria-pressed={armed} aria-disabled={busy || undefined}
                  onClick={unlessBusy(onToggle)}>
            Im Plan markieren
          </button>
          {armed && <p className="hint">Klicke in den Plan, wo die Schattenkante liegt.</p>}
        </>
      )}
      {mine.length > 0 && (
        <ul className="shadow-mark-panel__list">
          {mine.map((mark, index) => (
            <li key={mark.mark_id} className="shadow-mark-panel__item">
              <span className="shadow-mark-panel__when">{seenWords(mark.seen_at)}</span>
              <span>{readingWords(mark)}</span>
              <button type="button" className="link-button" aria-disabled={busy || undefined}
                      aria-label={`Markierung ${index + 1} vom ${seenWords(mark.seen_at)} löschen`}
                      onClick={unlessBusy(() => onRemove(mark.mark_id))}>
                Löschen
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
