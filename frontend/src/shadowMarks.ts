/**
 * Saying what a shadow mark found (doc 122).
 *
 * The server reads each mark against the model's shadow and says how far the
 * model's edge lies from it, which way, and which kind of edge it is. These
 * are that reading's words. At an edge a top casts, a length along the sun is
 * a height; where a shadow begins — a crown's, cast by where it starts — it is
 * where the shadow begins, and no height; beside the shadow, a miss round the
 * thing is a turn, and a turned shadow is most often a plan whose north is
 * off, so the words ask about it.
 */
import type { ShadowMark } from './api/client';

/** Below this the model meets the mark: a shadow's edge is blurred wider than that. */
const MET_M = 0.1;
/** Below this a height says nothing a gardener could measure. */
const HEIGHT_M = 0.05;

/** "0,8 m". */
function metres(value: number): string {
  return `${Math.abs(value).toFixed(1).replace('.', ',')} m`;
}

/** "4°", or "0,6°" under a degree, where the whole number would say none. */
function degrees(value: number): string {
  const size = Math.abs(value);
  return `${(size < 1 ? size.toFixed(1) : size.toFixed(0)).replace('.', ',')}°`;
}

/** What one mark found, in a sentence or two. */
export function readingWords(mark: ShadowMark): string {
  const reading = mark.reading;
  if (reading === null) return 'Dieses Element wirft zu diesem Zeitpunkt keinen Schatten mehr.';
  if (reading.offset_m < MET_M) return 'Das Modell trifft die Schattenkante.';
  const by = metres(reading.offset_m);
  if (reading.edge === 'near') {
    return `Im Modell beginnt der Schatten ${by} ${reading.model_longer ? 'früher' : 'später'}.`;
  }
  if (reading.edge === 'far') {
    const how = `Das Modell wirft den Schatten ${by} ${reading.model_longer ? 'zu weit' : 'zu kurz'}`;
    const height = reading.height_m;
    if (height === null || Math.abs(height) < HEIGHT_M) return `${how}.`;
    return `${how} — als stünde es ${metres(height)} ${height > 0 ? 'zu hoch' : 'zu niedrig'}.`;
  }
  const beside = `Das Modell wirft den Schatten ${by} seitlich daneben`;
  const turn = reading.turned_deg;
  if (turn === null) return `${beside}.`;
  const way = turn > 0 ? 'gegen den Uhrzeigersinn' : 'im Uhrzeigersinn';
  return `${beside} — um ${degrees(turn)} ${way} verdreht. Stimmt die Nordrichtung des Plans?`;
}

/** "21.06.2026, 11:30": when it was seen, on the gardener's clock. */
export function seenWords(seenAt: string): string {
  return new Date(seenAt).toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

/** Now, as a `datetime-local` field holds it: the gardener's own clock, to the minute. */
export function nowLocal(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
    + `T${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

/** A `datetime-local` value as the moment it names, or null when it names none. */
export function localToIso(value: string): string | null {
  if (value === '') return null;
  const moment = new Date(value);
  return Number.isNaN(moment.getTime()) ? null : moment.toISOString();
}
