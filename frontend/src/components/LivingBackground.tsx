/**
 * The particle field behind the front door.
 *
 * Three layers rather than three hundred elements: each one carries its whole
 * field of motes as repeated radial gradients in a single background image, so
 * the browser composites three layers and animates one transform on each. A
 * hundred animated nodes would be a hundred composited layers, and a canvas
 * would be a `requestAnimationFrame` loop running until the tab is closed.
 *
 * The three move at different speeds, which is the whole of the depth: the
 * small faint motes drift slowly far away, the larger ones climb past them.
 *
 * Everything here is decoration — `aria-hidden`, behind the content, and it
 * stops moving entirely under `prefers-reduced-motion`, where it stays as a
 * still field rather than vanishing and leaving an empty box.
 */
export function LivingBackground() {
  return (
    <div className="living" aria-hidden="true" data-testid="living-background">
      {/* Light from above, which is what makes the motes read as lit rather
          than as dots painted on. */}
      <div className="living__glow" />
      <div className="living__layer living__layer--far" />
      <div className="living__layer living__layer--mid" />
      <div className="living__layer living__layer--near" />
      {/* The bright band along the bottom: the motes rise *from* somewhere. */}
      <div className="living__floor" />
      {/* A few large, soft ones in front. Too many and the text behind them
          stops being readable, which is the one thing a background must not
          do. */}
      {[0, 1, 2, 3, 4].map((i) => (
        <span key={i} className={`living__bokeh living__bokeh--${i}`} />
      ))}
    </div>
  );
}
