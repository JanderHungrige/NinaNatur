import type { ChangeOut, ImprovementsOut, ScoreOut } from '../api/client';
import { insectGroup } from '../plural';

interface Props {
  score: ScoreOut;
  improvements: ImprovementsOut | null;
  onApply: (change: ChangeOut) => Promise<void>;
  busy: boolean;
}

const ORIGIN_LABEL: Record<string, string> = {
  native: 'heimisch',
  introduced: 'eingeführt',
  unknown: 'Herkunft unbekannt',
};

/** A verdict a reader can argue with, not a number to take on faith. */
export function InsectScore({ score, improvements, onApply, busy }: Props) {
  if (score.is_empty) {
    return (
      <section className="panel" aria-labelledby="score-heading">
        <h2 id="score-heading">Insektenwert</h2>
        <p className="empty">
          Noch nichts gepflanzt. Sobald Arten im Beet stehen, steht hier, wie viel
          sie Insekten bieten — und was am meisten brächte.
        </p>
      </section>
    );
  }

  const groups = Object.entries(score.by_group).filter(([, n]) => n > 0);

  return (
    <section className="panel" aria-labelledby="score-heading">
      <h2 id="score-heading">Insektenwert</h2>

      <p className="score-value">
        <strong>{score.score.toFixed(0)}</strong>
        <span className="score-of"> von 100</span>
      </p>
      <p className="hint">
        Gewichtet nach erfassten Beziehungen zu in Deutschland vorkommenden
        Insekten, und danach, ob die Tracht über die Saison durchhält. Ein voller
        Monat bringt keinen Zuwachs mehr — Lücken schon.
      </p>

      {groups.length > 0 && (
        <ul className="group-list">
          {groups.map(([group, n]) => (
            <li key={group}>{insectGroup(n, group)}</li>
          ))}
        </ul>
      )}

      <h3>Woraus er sich zusammensetzt</h3>
      <table className="contributions">
        <thead>
          <tr>
            <th scope="col">Art</th>
            <th scope="col">Partner</th>
            <th scope="col">Herkunft</th>
          </tr>
        </thead>
        <tbody>
          {score.by_species.map((s) => (
            <tr key={s.taxon_id}>
              <th scope="row">{s.canonical_name}</th>
              {/* Unknown stays unknown, at the last layer as at every other. */}
              <td>{s.german_partners === null ? 'nicht erfasst' : s.german_partners}</td>
              <td>{ORIGIN_LABEL[s.origin] ?? s.origin}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {score.plantings_without_interaction_data > 0 && (
        <p className="hint">
          Für {score.plantings_without_interaction_data} Pflanzung(en) liegen keine
          Beziehungsdaten vor. Sie zählen mit ihrem Grundwert — unbekannt ist nicht
          wertlos.
        </p>
      )}

      {improvements !== null && improvements.additions.length > 0 && (
        <>
          <h3>Was am meisten brächte</h3>
          <ul className="change-list">
            {improvements.additions.map((change) => (
              <li key={`${change.bed_id}-${change.taxon_id}`} className="change">
                <div className="change__main">
                  <span className="change__name">{change.canonical_name}</span>
                  <span className="change__reason">{change.reason}</span>
                </div>
                <span className="change__gain">
                  +{change.gain.toFixed(0)} → {change.resulting_score.toFixed(0)}
                </span>
                <button type="button" disabled={busy} onClick={() => void onApply(change)}>
                  Pflanzen
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      {improvements !== null && improvements.swaps.length > 0 && (
        <details className="swaps">
          {/* Deliberately behind a disclosure: a swap removes something, and the
              score will recommend removing a valuable plant whose month is
              already full. Additions are the safer advice. */}
          <summary>Wenn das Beet voll ist: austauschen</summary>
          <p className="hint">
            Ein Tausch entfernt eine Pflanze. Der Wert steigt auch dann, wenn die
            entfernte Art viele Partner hat — ihr Monat ist dann schlicht schon
            gedeckt.
          </p>
          <ul className="change-list">
            {improvements.swaps.map((change) => (
              <li key={`${change.replaces_planting_id}-${change.taxon_id}`} className="change">
                <div className="change__main">
                  <span className="change__name">
                    {change.replaces_name} → {change.canonical_name}
                  </span>
                  <span className="change__reason">{change.reason}</span>
                </div>
                <span className="change__gain">+{change.gain.toFixed(0)}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
