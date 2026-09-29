import type { Credit } from '../api/client';
import { ATTRIBUTION_URL } from '../map/tiles';

/**
 * Which survey said so (doc 106).
 *
 * A garden may rest on three of them now — ground from a state tile, a horizon
 * from Copernicus, roofs from a state building model — and every licence here
 * asks for the named credit. A height shown without it is a height used outside
 * its licence, so this is not a caption: it is the condition under which the
 * numbers above it may be shown at all. OpenStreetMap is one of them wherever
 * the plan draws its streets or houses (2026-09-21).
 *
 * Nothing is drawn where a garden rests on nothing, which is most of them.
 */
interface Props {
  credits: readonly Credit[];
}

/** What each source decided, in the gardener's words rather than the API's. */
const ABOUT: Record<string, string> = {
  ground: 'Gelände',
  horizon: 'Horizont',
  buildings: 'Gebäude',
  laser: 'Baumkronen',
  map: 'Karte',
  climate: 'Klima',
};

/** A credit whose terms ask for a link to them, by the source's name: OSM's
 *  attribution guideline wants "© OpenStreetMap-Mitwirkende" to lead to its
 *  copyright page, as it does in the map picker. */
const LINKED: Record<string, string> = {
  OpenStreetMap: ATTRIBUTION_URL,
};

const decided = (about: string): string =>
  about.split(', ').map((part) => ABOUT[part] ?? part).join(' und ');

export function SourceCredits({ credits }: Props) {
  if (credits.length === 0) return null;
  return (
    <section className="panel source-credits" aria-labelledby="source-credits">
      <h3 id="source-credits" className="panel__title">Woher die Zahlen kommen</h3>
      <ul className="source-credits__list">
        {credits.map((credit) => (
          <li key={`${credit.name}-${credit.about}`} className="source-credits__item">
            <span className="source-credits__what">
              {decided(credit.about)}: {credit.name}
              {credit.detail === null || credit.detail === undefined ? '' : ` · ${credit.detail}`}
            </span>
            {/* The credit itself, word for word as the licence asks, and the
                licence, named and linked as CC BY 4.0 asks (§ 3(a)(1)(C)). */}
            <span className="source-credits__credit">
              {LINKED[credit.name] === undefined ? credit.attribution : (
                <a href={LINKED[credit.name]} target="_blank" rel="noreferrer noopener">
                  {credit.attribution}
                </a>
              )}
            </span>
            <span className="source-credits__credit">
              {'Lizenz '}
              {credit.licence_url ? (
                <a href={credit.licence_url} target="_blank" rel="noreferrer noopener license">
                  {credit.licence}
                </a>
              ) : credit.licence}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
