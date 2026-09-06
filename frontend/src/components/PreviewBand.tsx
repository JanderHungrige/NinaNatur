interface Props {
  /** What `/healthz` says this deployment is called. */
  environment: string | null;
}

/**
 * A band across the top of anything that is not the live site.
 *
 * The preview and production are the same application, byte for byte — that is
 * the point of a preview and it is also the danger. Somebody who draws a garden
 * on the wrong one loses it the next time that volume is cleared, and there is
 * nothing on the page to tell them apart.
 *
 * **A band, not a corner label.** It has to survive being ignored: a discreet
 * marker is exactly what somebody stops seeing on the second day, which is the
 * day they start trusting the page.
 *
 * Nothing is shown on production. A page that announces itself as production is
 * noise on the site that matters most, and it would also be the thing that
 * appears by mistake if the environment were ever unset.
 */
export function PreviewBand({ environment }: Props) {
  if (environment === null || environment === 'prod') return null;

  return (
    <div className="preview-band" role="status">
      <strong>Vorschau ({environment})</strong> — hier angelegte Gärten sind zum
      Ausprobieren und werden nicht aufgehoben. Der richtige Garten wohnt auf{' '}
      <a href="https://ninanatur.w3rth.de">ninanatur.w3rth.de</a>.
    </div>
  );
}
