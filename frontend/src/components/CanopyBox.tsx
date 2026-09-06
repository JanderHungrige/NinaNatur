import type { CanopySuggestion } from '../api/client';

interface Props {
  suggestions: CanopySuggestion[];
  onAccept: (suggestionId: number) => void;
  onDismiss: (suggestionId: number) => void;
  busy: boolean;
}

/**
 * Trees the surface model found and nobody has drawn.
 *
 * The single most common thing that shades a German garden is a large tree, and
 * until now one existed in this model only if somebody drew it. A neighbour's
 * beech is exactly the thing a person forgets, because it is not theirs.
 *
 * **Suggestions, never objects.** A crown, a hedge, a marquee and a
 * badly-mapped building all read as "tall, and not ground" to a laser. So they
 * are offered with what is actually known — how tall, how wide, how far away —
 * and the gardener decides. Same standing as Wave 16's misplacement warning.
 *
 * Dismissing is as prominent as accepting. A list where refusing is the harder
 * click is a list that gets accepted by exhaustion.
 */
export function CanopyBox({ suggestions, onAccept, onDismiss, busy }: Props) {
  if (suggestions.length === 0) return null;

  return (
    <section className="panel canopy-box" aria-labelledby="canopy-heading">
      <h2 id="canopy-heading">Bäume in der Nähe</h2>
      <p className="hint">
        Aus Laserdaten gemessen — {suggestions.length === 1 ? 'einer' : 'welche'}, die
        noch nicht im Plan {suggestions.length === 1 ? 'steht' : 'stehen'}. Die Art
        weiß niemand; der Schatten rechnet dann mit einem Laubbaum.
      </p>
      <ul className="canopy-box__list">
        {suggestions.map((tree) => (
          <li key={tree.suggestion_id}>
            <span className="canopy-box__what">
              {tree.height_m.toFixed(1).replace('.', ',')} m hoch,{' '}
              {(tree.radius_m * 2).toFixed(1).replace('.', ',')} m breit ·{' '}
              {Math.round(Math.hypot(tree.x, tree.y))} m entfernt
            </span>
            <span className="canopy-box__actions">
              <button type="button" disabled={busy} onClick={() => onAccept(tree.suggestion_id)}>
                Eintragen
              </button>
              <button type="button" disabled={busy} onClick={() => onDismiss(tree.suggestion_id)}>
                Gibt es nicht
              </button>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
