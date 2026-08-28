import type { BedSuggestions } from '../api/client';
import { birds } from '../plural';

interface Props {
  suggestions: BedSuggestions | null;
  /** Whether woody plants are in the list — the hint claimed they never were. */
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
function describeFit(axes: BedSuggestions['items'][number]['fit']['axes']): string {
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

  return (
    <section className="panel" aria-labelledby="suggestions-heading">
      <h2 id="suggestions-heading">Vorschläge für {suggestions.bed_name}</h2>
      <p className="hint">
        {suggestions.total} passende Arten, gewertet nach den Standortwerten dieses
        Beetes.{' '}
        {includeTrees
          ? 'Bäume und Sträucher sind dabei.'
          : 'Bäume und Sträucher sind ausgeblendet.'}
      </p>
      {suggestions.items.some((i) => (i.bird_partners ?? 0) > 0) && (
        <p className="hint">
          „Als Nahrung“ zählt Vogelarten, für die erfasst ist, dass sie diese
          Pflanze fressen — meist Früchte oder Samen. Die Zahl steht neben dem
          Insektenwert, nicht darin.
        </p>
      )}

      <ul className="suggestion-list">
        {suggestions.items.map((item) => (
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
              {/* Shown only when there is something to show. A "0 Vogelarten"
                  on every herbaceous plant is noise, and on a species GloBI
                  has no records for at all it would be a claim we cannot make. */}
              {item.bird_partners !== null && item.bird_partners > 0 && (
                <span className="suggestion__birds">
                  {birds(item.bird_partners)} als Nahrung
                </span>
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
        ))}
      </ul>
    </section>
  );
}
