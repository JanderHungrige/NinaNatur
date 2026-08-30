import type { SightlinesOut } from '../api/client';

interface Props {
  result: SightlinesOut;
  onClear: () => void;
}

function metres(value: number): string {
  return `${value.toLocaleString('de-DE', { maximumFractionDigits: 1 })} m`;
}

/**
 * What is visible from where the user is standing.
 *
 * The value is not the novelty. "Will I actually see this plant" is the question
 * that decides where things go, and it has been a guess until now.
 */
export function Sightlines({ result, onClear }: Props) {
  const { plantings, estimated_count: estimated } = result;

  return (
    <section className="panel sightlines" aria-labelledby="sightlines-heading">
      <div className="sightlines__head">
        <h2 id="sightlines-heading">Von hier aus sichtbar</h2>
        <button type="button" className="link-button" onClick={onClear}>
          Standpunkt entfernen
        </button>
      </div>

      {estimated > 0 && (
        <p className="hint">
          {estimated === 1 ? '1 Antwort beruht' : `${estimated} Antworten beruhen`} auf
          geschätzten Höhen aus der Karte — korrigiere das Gebäude im Plan, wenn du
          es genauer weißt.
        </p>
      )}

      <ul className="sightlines__list">
        {plantings.map((p) => (
          <li key={p.planting_id}>
            <span className="sightlines__name">{p.name}</span>
            {/* Unknown stays unknown, at this layer as at every other. */}
            {p.visible === null ? (
              <span className="hint">Höhe nicht erfasst — keine Aussage möglich</span>
            ) : p.visible ? (
              <span className="sightlines__visible">sichtbar</span>
            ) : (
              <span className="sightlines__hidden">
                verdeckt — sichtbar ab {metres(p.visible_from_m ?? 0)}
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
