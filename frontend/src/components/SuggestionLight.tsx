import type { BedSuggestions } from '../api/client';

/*
 * What a bed's suggestions say about the light they were ranked by — owner
 * review #9 (2026-09-21). The header used to claim "gewertet nach den
 * Standortwerten dieses Beetes" for a bed whose light had never been computed.
 */

type LightState = BedSuggestions['light_state'];

const HINTS: Partial<Record<LightState, string>> = {
  missing: 'Licht noch nicht berechnet — die Liste berücksichtigt nur den Boden.',
  stale:
    'Der Schatten wurde seit der letzten Änderung im Garten nicht neu berechnet — ' +
    'die Liste rechnet noch mit dem alten Licht.',
};

/** What the list could not rank by, in words. Null when the light is current
 *  and the list really was ranked by the bed's whole site. */
export function lightHint(state: LightState): string | null {
  return HINTS[state] ?? null;
}

/** "4 Arten, denen es hier zu hell ist, sind ausgeblendet." — or nothing. */
export function hiddenByLight(counts: BedSuggestions['filters']): string | null {
  const hidden = counts.light?.excluded ?? 0;
  if (hidden === 0) return null;
  const n = hidden.toLocaleString('de-DE');
  return hidden === 1
    ? `${n} Art, der es hier zu hell ist, ist ausgeblendet.`
    : `${n} Arten, denen es hier zu hell ist, sind ausgeblendet.`;
}

interface Props {
  state: LightState;
  busy: boolean;
  /** The sun panel's rebuild. Without it, the note still says what is missing. */
  onComputeShade?: (() => void) | undefined;
}

/** The reason, and „Schatten berechnen“, where the light is missing or stale. */
export function LightNote({ state, busy, onComputeShade }: Props) {
  const hint = lightHint(state);
  if (hint === null) return null;
  return (
    <>
      <p className="hint">{hint}</p>
      {onComputeShade !== undefined && (
        // In reach while a request runs, and ignored: a button disabled under
        // the keyboard's focus throws the focus to the page (doc 88, rule 11).
        <button
          type="button"
          className="suggestions__shade"
          aria-disabled={busy || undefined}
          onClick={() => {
            if (!busy) onComputeShade();
          }}
        >
          Schatten berechnen
        </button>
      )}
    </>
  );
}
