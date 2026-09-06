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
