/**
 * The roof shapes the shading model has a ratio for.
 *
 * Mirrors `ninanatur/garden/roofs.py::Roof`, and a pytest guard fails if the
 * two fall out of step — the kind vocabulary learnt that lesson once already,
 * when a dropdown went on offering a value the server had stopped knowing.
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

/** Kinds a roof is a sensible question for. A pond has no roof. */
export const ROOFED = new Set(['house', 'shed']);
