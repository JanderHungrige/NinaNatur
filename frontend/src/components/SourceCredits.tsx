import type { Credit } from '../api/client';

/**
 * Which survey said so (doc 106).
 *
 * A garden may rest on three of them now — ground from a state tile, a horizon
 * from Copernicus, roofs from a state building model — and every licence here
 * asks for the named credit. A height shown without it is a height used outside
 * its licence, so this is not a caption: it is the condition under which the
 * numbers above it may be shown at all.
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
            {/* The credit itself, word for word as the licence asks. */}
            <span className="source-credits__credit">{credit.attribution}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
