interface Props {
  /** What is being waited for, in words. Never a percentage: nothing here measures one. */
  label: string;
  className?: string | undefined;
  /** Three rising motes instead of the ring, for the front door's meadow. */
  motes?: boolean | undefined;
}

/**
 * Something is happening, and what (doc 87).
 *
 * Indeterminate on purpose: the server says when a request is done, never how
 * far along it is, so the words say what is being worked on and nothing claims
 * a share of it.
 *
 * Shown, not announced. The mark is `aria-hidden` and the label is plain text:
 * the status toast is the page's one live region, and it says when a long wait
 * starts and when it ends. A second region repeating "wird berechnet" beside it
 * would only be noise. Under `prefers-reduced-motion` the mark stands still.
 */
export function Working({ label, className, motes = false }: Props) {
  const classes = ['working'];
  if (motes) classes.push('working--motes');
  if (className !== undefined) classes.push(className);

  return (
    <span className={classes.join(' ')}>
      {motes ? (
        <span className="working__motes" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
      ) : (
        <span className="working__spinner" aria-hidden="true" />
      )}
      <span className="working__label">{label}</span>
    </span>
  );
}
