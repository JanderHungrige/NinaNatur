import { type ReactNode, useId } from 'react';

interface Props {
  open: boolean;
  onToggle: (open: boolean) => void;
  /** Always there: stepping through the months still moves the plan when the table is folded. */
  player: ReactNode;
  children: ReactNode;
}

/**
 * Everything that is time, in one place under the plan (doc 87).
 *
 * The heading is the disclosure: its button carries `aria-expanded`, so the name
 * stays and only the state changes. It is *Jahreslauf* rather than *Blühjahr*,
 * which is already the heading of the table inside. The player stays outside
 * the folding body, because folding the table away is not stopping the year.
 */
export function TimelineDock({ open, onToggle, player, children }: Props) {
  const bodyId = useId();

  return (
    <footer className="timeline-dock">
      <div className="timeline-dock__bar">
        <h2 className="timeline-dock__heading">
          <button
            type="button"
            className="timeline-dock__toggle"
            aria-expanded={open}
            aria-controls={bodyId}
            onClick={() => onToggle(!open)}
          >
            Jahreslauf
          </button>
        </h2>
        {player}
      </div>
      <div id={bodyId} className="timeline-dock__body" hidden={!open}>
        {children}
      </div>
    </footer>
  );
}
