import { useEffect, useRef, useState } from 'react';

import type { SpeciesInfoOut } from '../api/client';
import { NinaNaturClient } from '../api/client';

const defaultClient = new NinaNaturClient();

/**
 * Hoisted deliberately. As an inline default parameter this closure would be a
 * fresh identity on every render, and it is an effect dependency below — the
 * effect would cancel and refire itself forever, hammering Wikipedia in a loop
 * while the panel sat on "Wird geladen…". A default that feeds a dependency
 * array has to be a stable reference.
 */
const defaultLoad = (taxonId: number): Promise<SpeciesInfoOut | null> =>
  defaultClient.speciesInfo(taxonId);

interface Props {
  taxonId: number;
  canonicalName: string;
  onClose: () => void;
  /**
   * How to fetch the article. Injected rather than reached for, like every other
   * boundary in this project: a module-level client binds `globalThis.fetch` at
   * import time, which makes the component untestable without stubbing globals
   * and hides which collaborator it actually depends on.
   */
  load?: (taxonId: number) => Promise<SpeciesInfoOut | null>;
}

/**
 * What a plant actually is.
 *
 * The extract is Wikipedia's under CC-BY-SA, so the credit and the link back are
 * part of the content, not an optional footer — a cached copy does not become
 * ours. The text is rendered as text; nothing from Wikipedia is interpreted as
 * markup.
 */
export function SpeciesInfo({
  taxonId,
  canonicalName,
  onClose,
  load = defaultLoad,
}: Props) {
  const [info, setInfo] = useState<SpeciesInfoOut | null>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'missing' | 'failed'>('loading');
  const panel = useRef<HTMLElement | null>(null);

  /**
   * Bring it to where the reader is.
   *
   * It renders under a suggestion list that can be several thousand pixels
   * long, so clicking "Info" on the first row opened it four screens below the
   * viewport — which reads as the button doing nothing at all. Focus goes with
   * the scroll, because somebody working from the keyboard has exactly the same
   * problem and no scrollbar to notice it with.
   */
  useEffect(() => {
    // Optional call: jsdom has no scrollIntoView, and neither has every browser
    // this might run in.
    // 'center' and no smoothing: 'nearest' does the least it can get away
    // with, and a smooth scroll that is still running when the user looks is
    // indistinguishable from no scroll at all.
    panel.current?.scrollIntoView?.({ block: 'center' });
    panel.current?.focus();
  }, [taxonId]);

  useEffect(() => {
    let cancelled = false;
    // Drop the previous species' article. React reuses this component instance
    // across a click on a different plant, so without this the heading keeps
    // showing the last species' title while the subtitle already shows the new
    // one — the panel names two different plants at once until the fetch lands.
    setInfo(null);
    setState('loading');
    load(taxonId)
      .then((result) => {
        if (cancelled) return;
        setInfo(result);
        setState(result === null ? 'missing' : 'ready');
      })
      .catch(() => {
        // The panel degrades; a plant list must not break because Wikipedia is down.
        if (!cancelled) setState('failed');
      });
    return () => {
      cancelled = true;
    };
  }, [taxonId, load]);

  return (
    <section
      ref={panel}
      className="panel info-panel"
      aria-labelledby="info-heading"
      tabIndex={-1}
    >
      <div className="info-panel__head">
        <h2 id="info-heading">{info?.title ?? canonicalName}</h2>
        <button type="button" className="link-button" onClick={onClose}>
          Schließen
        </button>
      </div>
      <p className="hint">
        <em>{canonicalName}</em>
      </p>

      {state === 'loading' && <p className="hint">Wird geladen…</p>}

      {state === 'missing' && (
        <p className="hint">
          Zu dieser Art gibt es keinen Wikipedia-Artikel — weder auf Deutsch noch
          auf Englisch.
        </p>
      )}

      {state === 'failed' && (
        <p className="hint">
          Die Beschreibung konnte gerade nicht geladen werden. Alles andere zu
          dieser Art steht weiterhin zur Verfügung.
        </p>
      )}

      {state === 'ready' && info !== null && (
        <>
          {info.thumbnail_url !== null && (
            <img
              className="info-panel__image"
              src={info.thumbnail_url}
              alt={`${info.title} — Foto aus Wikipedia`}
              loading="lazy"
            />
          )}
          <p className="info-panel__extract">{info.extract}</p>
          {info.language !== 'de' && (
            <p className="hint">
              Kein deutscher Artikel vorhanden — angezeigt wird der englische.
            </p>
          )}
          {/* Attribution is a condition of use, not a footer we may drop. */}
          <p className="hint attribution">
            Text und Bild aus{' '}
            <a href={info.page_url} target="_blank" rel="noreferrer noopener">
              Wikipedia
            </a>
            , Lizenz {info.licence}.
          </p>
        </>
      )}
    </section>
  );
}
