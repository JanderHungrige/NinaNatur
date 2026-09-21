import { Working } from './Working';

interface Props {
  /** How many corners have been set. */
  points: number;
  busy: boolean;
  /** The garden is being made from the outline. */
  creating: boolean;
  onUndo: () => void;
  onCreate: () => void;
  problem: string | null;
}

/**
 * The map's last row: how many corners, take the last one back, and make the
 * garden (doc 31).
 *
 * Making it is not a blink. The server asks OpenStreetMap for every building
 * and street within fifty metres before the garden exists, so the button says
 * it is at work and a line under it says with what — in words that promise
 * seconds, not a share of them.
 */
export function MapPickerActions({ points, busy, creating, onUndo, onCreate, problem }: Props) {
  return (
    <>
      <div className="map-picker__actions">
        <span className="hint">
          {points} {points === 1 ? 'Punkt' : 'Punkte'}
        </span>
        <button type="button" aria-label="Rückgängig" disabled={busy || points === 0} onClick={onUndo}>
          ↶
        </button>
        <button type="button" onClick={onCreate} disabled={busy || creating}>
          {creating ? <Working label="Wird angelegt…" /> : 'Garten anlegen'}
        </button>
      </div>
      {creating && (
        <p className="hint map-picker__creating">
          Gebäude und Straßen aus OpenStreetMap werden übernommen — das dauert ein
          paar Sekunden.
        </p>
      )}
      {problem !== null && (
        <p className="hint" role="alert">
          {problem}
        </p>
      )}
    </>
  );
}
