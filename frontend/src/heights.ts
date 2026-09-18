/**
 * Saying where a building's height came from.
 *
 * Every height in this plan is one of three things and they are not
 * interchangeable: a survey measured it, this model measured it from a laser
 * raster, or somebody assumed it. A shading map resting on an assumption must
 * not look like one resting on a measurement — that is the same rule the trait
 * layer has followed since Wave 1, applied to the other half of the model.
 *
 * The user's own entry is deliberately unlabelled. They know they typed it, and
 * a badge saying "you said so" on the one value somebody is sure about is noise.
 */

import { EAVES_FRACTION } from './roofs';

/** What the server can say, in the order of how much it is worth. */
export const HEIGHT_SOURCES: Readonly<Record<string, string>> = {
  user: '',
  surveyed: 'amtlich vermessen',
  measured: 'aus Laserdaten gemessen',
  osm_height: 'aus OpenStreetMap',
  osm_levels: 'aus Geschosszahl geschätzt',
  neighbourhood: 'für die Gegend angenommen',
};

/** The words for one height's provenance, or null when there is nothing to say. */
export function heightNote(source: string | null | undefined): string | null {
  if (source === null || source === undefined) return null;
  const text = HEIGHT_SOURCES[source];
  // An unknown value is not silently dropped: a server that starts sending a
  // new one should show it rather than quietly look like a user entry.
  if (text === undefined) return source;
  return text === '' ? null : text;
}

/** Whether this height is a measurement rather than a guess. */
export function isMeasured(source: string | null | undefined): boolean {
  return source === 'surveyed' || source === 'measured';
}

/**
 * Where a roof's shape came from (doc 93). The same rule as the heights: the
 * gardener's own answer is unlabelled, and "weiß nicht" is nobody's answer, so
 * it names no source either.
 */
export const ROOF_SOURCES: Readonly<Record<string, string>> = {
  user: '',
  surveyed: 'amtlich vermessen',
  osm: 'aus OpenStreetMap',
};

/** The words for where this roof shape came from, or null when there is nothing to say. */
export function roofNote(roof: string, source: string): string | null {
  if (roof === 'unknown') return null;
  const text = ROOF_SOURCES[source];
  if (text === undefined) return source;
  return text === '' ? null : text;
}

/** "6,8 m": metres as the page writes them. */
function metres(value: number): string {
  return `${value.toFixed(1).replace('.', ',')} m`;
}

/**
 * The words for where an eaves height came from (doc 93).
 *
 * The eaves decide the pitch, and the pitch how much darker a north roof is than
 * a south one — so the assumption the model makes when nobody gave them is said,
 * with its number when the ridge is known. A value stored before anybody kept
 * track owns up to that rather than borrowing a source.
 */
export function eavesNote(
  eavesM: number | null,
  source: string | null,
  ridgeM: number | null,
): string | null {
  if (eavesM === null) {
    const assumed = 'Nicht bekannt: gerechnet wird mit drei Vierteln der Firsthöhe';
    return ridgeM === null ? assumed : `${assumed}, ${metres(EAVES_FRACTION * ridgeM)}`;
  }
  if (source === null) return 'Herkunft nicht vermerkt';
  return heightNote(source);
}
