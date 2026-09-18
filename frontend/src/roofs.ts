/**
 * The roof shapes the shading model has a ratio for.
 *
 * Mirrors `ninanatur/garden/roofs.py::Roof`, and a pytest guard fails if the
 * two fall out of step (`tests/test_kind_vocabulary.py`, since Wave 21 — before
 * that this said so and nothing checked) — the kind vocabulary learnt that
 * lesson once already, when a dropdown went on offering a value the server had
 * stopped knowing.
 *
 * Asked because OSM's `height` is the ridge: without a shape a house is
 * modelled as solid to it, and shades too much all season. It is also one of
 * the few things somebody can answer by looking out of the window.
 */
export const ROOFS: ReadonlyArray<readonly [string, string]> = [
  ['unknown', 'weiß nicht'],
  ['gable', 'Satteldach'],
  ['hip', 'Walmdach'],
  ['pent', 'Pultdach'],
  ['flat', 'Flachdach'],
  // Surveyed answers, added in Wave 19 when the official models turned out to
  // give them. A fifth of German buildings are Mischform, and until now
  // somebody with one had to lie to this list.
  ['mix', 'Mischform'],
  ['other', 'andere Form'],
];

/**
 * Where the eaves are when nobody has said: three quarters of the way up.
 *
 * Mirrors `ninanatur/garden/roofs.py::DEFAULT_EAVES_FRACTION`, and a pytest
 * guard holds the two together — the page says what the model assumed (doc 93),
 * so it has to assume the same thing.
 */
export const EAVES_FRACTION = 0.75;

/** Kinds a roof is a sensible question for. A pond has no roof. */
export const ROOFED = new Set(['house', 'shed']);

/** A ridge runs both ways, so four words cover it; a fall runs one way, so eight. */
const RIDGES = ['Nord–Süd', 'Nordost–Südwest', 'Ost–West', 'Südost–Nordwest'] as const;
const FALLS = [
  'Norden', 'Nordosten', 'Osten', 'Südosten', 'Süden', 'Südwesten', 'Westen', 'Nordwesten',
] as const;

/** The nearest of `words`, spread evenly around a circle of `period` degrees. */
function nearest(words: readonly string[], bearing: number, period: number): string {
  const step = period / words.length;
  const index = Math.round((((bearing % period) + period) % period) / step) % words.length;
  return words[index] ?? words[0] ?? '';
}

/**
 * Which way the ridge runs and the pitch it gives, in words (doc 94).
 *
 * The direction is the survey's where there is one — only the survey sets a
 * fall — and the page says so; otherwise the model's assumption, said as one.
 * The pitch follows from the eaves, whose own note says where they came from.
 */
export function ridgeNote(
  roof: string,
  fallDeg: number | null,
  pitchDeg: number | null,
): string | null {
  const pitch = pitchDeg === null ? '' : ` · Neigung ${Math.round(pitchDeg)}°`;
  if (roof === 'pent') {
    if (fallDeg === null) return 'Gefälle unbekannt: gerechnet wie ein Flachdach';
    return `Fällt nach ${nearest(FALLS, fallDeg, 360)} (amtlich vermessen)${pitch}`;
  }
  if (roof !== 'gable' && roof !== 'hip') return null;
  if (fallDeg === null) return `First entlang der längeren Seite (angenommen)${pitch}`;
  return `First ${nearest(RIDGES, fallDeg + 90, 180)} (amtlich vermessen)${pitch}`;
}
