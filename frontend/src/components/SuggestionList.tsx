import type { BedSuggestions } from '../api/client';
import { birds } from '../plural';

type Suggestion = BedSuggestions['items'][number];

interface Props {
  suggestions: BedSuggestions | null;
  /** Whether woody plants are listed — the hint used to claim they never were. */
  includeTrees: boolean;
  onPlant: (taxonId: number, name: string) => Promise<void>;
  onShowInfo: (taxonId: number, name: string) => void;
  busy: boolean;
}

const BAND_LABEL: Record<string, string> = {
  optimal: 'optimal',
  suitable: 'passend',
  borderline: 'grenzwertig',
  unsuitable: 'ungeeignet',
};

/** "Licht optimal · Feuchte grenzwertig" — why this plant, in words. */
function describeFit(axes: Suggestion['fit']['axes']): string {
  const names: Record<string, string> = {
    ellenberg_l: 'Licht',
    ellenberg_m: 'Feuchte',
    ellenberg_n: 'Nährstoffe',
    ellenberg_r: 'pH',
  };
  return Object.entries(axes)
    .map(([axis, fit]) => `${names[axis] ?? axis} ${BAND_LABEL[fit.band] ?? fit.band}`)
    .join(' · ');
}

export function SuggestionList({
  suggestions,
  includeTrees,
  onPlant,
  onShowInfo,
  busy,
}: Props) {
  if (suggestions === null) {
    return (
      <section className="panel">
        <h2>Vorschläge</h2>
        <p className="hint">Wähle ein Beet, um passende Arten zu sehen.</p>
      </section>
    );
  }

  const row = (item: Suggestion) => (
    <li key={item.taxon_id} className="suggestion">
      <div className="suggestion__main">
        <span className="suggestion__name">{item.canonical_name}</span>
        <span className="suggestion__fit">{describeFit(item.fit.axes)}</span>
      </div>
      <div className="suggestion__meta">
        {/* Unknown stays unknown, at the last layer as at every other. */}
        <span>{item.flower_colour ?? 'Farbe unbekannt'}</span>
        <span>
          {item.flowering_start_month !== null && item.flowering_end_month !== null
            ? `Blüte ${item.flowering_start_month}–${item.flowering_end_month}`
            : 'Blühzeit unbekannt'}
        </span>
        {/* Shown only when there is something to show. A "0 Vogelarten" on every
            herbaceous plant is noise, and on a species GloBI holds no records
            for at all it would be a claim the data cannot support. */}
        {item.bird_partners !== null && item.bird_partners > 0 && (
          <span className="suggestion__birds">{birds(item.bird_partners)} als Nahrung</span>
        )}
        {/* Priced, not hidden. A tree in a small bed is a decision the user is
            entitled to make, once they can see what it would actually take. */}
        {item.fits_bed === false && item.space_m2 !== null && (
          <span className="suggestion__space">braucht ~{Math.round(item.space_m2)} m²</span>
        )}
      </div>
      <div className="suggestion__actions">
        <button
          type="button"
          className="icon-button"
          aria-label={`Informationen zu ${item.canonical_name}`}
          onClick={() => onShowInfo(item.taxon_id, item.canonical_name)}
        >
          Info
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void onPlant(item.taxon_id, item.canonical_name)}
        >
          Pflanzen
        </button>
      </div>
    </li>
  );

  const showsBirds = [...suggestions.items, ...suggestions.woody].some(
    (i) => (i.bird_partners ?? 0) > 0,
  );

  return (
    <section className="panel" aria-labelledby="suggestions-heading">
      <h2 id="suggestions-heading">Vorschläge für {suggestions.bed_name}</h2>
      <p className="hint">
        {suggestions.total} passende Arten, gewertet nach den Standortwerten dieses
        Beetes.{' '}
        {includeTrees
          ? 'Gehölze stehen weiter unten in einer eigenen Liste.'
          : 'Bäume und Sträucher sind ausgeblendet.'}
      </p>
      {showsBirds && (
        <p className="hint">
          „Als Nahrung“ zählt Vogelarten, für die erfasst ist, dass sie diese
          Pflanze fressen — meist Früchte oder Samen. Die Zahl steht neben dem
          Insektenwert, nicht darin.
        </p>
      )}

      <ul className="suggestion-list">{suggestions.items.map(row)}</ul>

      {suggestions.woody.length > 0 && (
        <>
          <h3>Gehölze für diesen Standort</h3>
          <p className="hint">
            Sträucher und Bäume passen selten in ein Beet und tragen am meisten —
            sie führen den Katalog bei Insekten wie bei Vögeln an. Was mehr Platz
            braucht, als dieses Beet hat, steht mit seinem Platzbedarf dabei. Ein
            gepflanztes Gehölz verschattet anschließend sein Beet und die
            Nachbarbeete, und die Vorschläge dort ändern sich entsprechend.
          </p>
          <ul className="suggestion-list suggestion-list--woody">
            {suggestions.woody.map(row)}
          </ul>
        </>
      )}
    </section>
  );
}
