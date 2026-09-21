interface Props {
  /** Which panel this holds the place of, for a test or a stylesheet to find. */
  of: string;
  /** Lines of text under the heading's bar. */
  lines?: number | undefined;
}

/**
 * The place a panel will take, while its answer is on the way (doc 87).
 *
 * Quiet on purpose: grey bars in the panel's own box, breathing slowly, still
 * under `prefers-reduced-motion`. The point is that nothing jumps when the
 * answers arrive and that the empty space reads as "coming" rather than as
 * "nothing here". Hidden from assistive technology: the toast says when the
 * garden has loaded, and a list of empty bars says nothing.
 */
export function Skeleton({ of, lines = 3 }: Props) {
  return (
    <div className="panel skeleton" aria-hidden="true" data-skeleton={of}>
      <span className="skeleton__line skeleton__line--title" />
      {Array.from({ length: lines }, (_, index) => (
        <span key={index} className="skeleton__line" />
      ))}
    </div>
  );
}
