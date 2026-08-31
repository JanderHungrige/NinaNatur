import { type ReactNode, useEffect, useState } from 'react';

import type { StatsOut } from '../api/client';

interface Props {
  /**
   * The create-a-garden form, rendered as-is.
   *
   * A slot rather than a button, because a garden's latitude is not a detail:
   * the whole solar model rests on it, and a landing page that created gardens
   * in Berlin by default would quietly compute everyone's light for Berlin.
   */
  createForm: ReactNode;
  /** Finding the garden on a map — the way most people will actually start. */
  mapPicker?: ReactNode;
  /** The signed-in visitor's own gardens. Absent when nobody is signed in. */
  myGardens?: ReactNode;
  onOpen: (token: string) => void;
  busy: boolean;
  loadStats: () => Promise<StatsOut | null>;
  problem?: string | undefined;
}

function de(n: number): string {
  return n.toLocaleString('de-DE');
}

/**
 * The front door.
 *
 * Wave 1 had this page and it was liked; Wave 3 replaced it with a form when the
 * React app took the root route. It comes back as the place where someone
 * chooses *which* garden they are working on — new, or one they already have.
 *
 * The figures come from the API. Wave 1 wrote "3.087 Arten" into its HTML by
 * hand, and it was wrong the first time the catalogue was rebuilt: a page that
 * states a number is making a claim.
 */
export function Landing({
  createForm,
  mapPicker,
  myGardens,
  onOpen,
  busy,
  loadStats,
  problem,
}: Props) {
  const [stats, setStats] = useState<StatsOut | null>(null);
  const [id, setId] = useState('');

  useEffect(() => {
    let cancelled = false;
    // The front door opens whether or not the catalogue answers.
    loadStats()
      .then((s) => {
        if (!cancelled) setStats(s);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [loadStats]);

  const open = () => {
    const trimmed = id.trim();
    if (trimmed !== '') onOpen(trimmed);
  };

  return (
    <div className="landing">
      <div className="hero">
        <div className="hero__content">
      <h1 className="landing__title">
        Ein Garten, der
        <br />
        etwas ernährt.
      </h1>
      <p className="landing__lede">
        NinaNatur plant Beete mit heimischen Pflanzen — passend zum Standort,
        über das Jahr durchblühend, und messbar wertvoll für Insekten und Vögel.
      </p>

      {stats !== null && (
        <dl className="landing__stats">
          <div className="stat">
            <dt>Arten im Katalog</dt>
            <dd>{de(stats.species)}</dd>
          </div>
          <div className="stat">
            <dt>davon mit vollem Standortprofil</dt>
            <dd>{de(stats.species_with_full_site_profile)}</dd>
          </div>
          <div className="stat">
            <dt>erfasste Beziehungen zu heimischen Tieren</dt>
            <dd>{de(stats.animal_partnerships)}</dd>
          </div>
        </dl>
      )}
        </div>
      </div>

      {/* Somebody signed in has already made gardens; offering to make
          another before showing them is the wrong order. */}
      {myGardens !== undefined && <div className="landing__mine">{myGardens}</div>}

      {/* One way in, not three. Three equal boxes said three equal choices;
          there is one, and "Garten öffnen" beside it is not a way of making a
          garden but of coming back to one. */}
      <div className="landing__ways">
        {mapPicker !== undefined && (
          <section className="panel landing__way landing__way--wide">
            <h2>Auf der Karte anfangen</h2>
            {mapPicker}
          </section>
        )}
        <section className="panel landing__way">
          <h2>Garten öffnen</h2>
          <label htmlFor="landing-id">Garten-ID</label>
          <input
            id="landing-id"
            type="text"
            value={id}
            disabled={busy}
            placeholder="ID aus deinem Garten"
            onChange={(e) => setId(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') open();
            }}
          />
          <p className="hint">
            Solange es noch keine Konten gibt, ist die ID der einzige Weg zurück.
          </p>
          <button type="button" onClick={open} disabled={busy}>
            Garten öffnen
          </button>
          {problem !== undefined && (
            <p className="hint" role="alert">
              {problem}
            </p>
          )}
        </section>
      </div>

      {/* Kept as a quiet way rather than removed, decided with the user:
          Nominatim and Overpass are free services with no SLA, and without this
          a bad afternoon at either leaves nobody able to start at all. */}
      <details className="landing__aside">
        <summary>Ohne Karte anfangen</summary>
        <p className="hint">
          Wenn die Kartensuche gerade nicht antwortet, oder du die Koordinaten
          ohnehin kennst.
        </p>
        {createForm}
      </details>

      {stats !== null && (
        <footer className="landing__sources">
          <p className="hint">Alle Daten aus offen lizenzierten Quellen:</p>
          <ul>
            {stats.sources.map((s) => (
              <li key={s.name}>
                <a href={s.url} target="_blank" rel="noreferrer noopener">
                  {s.name}
                </a>{' '}
                — {s.contributes}, {s.licence}
              </li>
            ))}
          </ul>
        </footer>
      )}
    </div>
  );
}
