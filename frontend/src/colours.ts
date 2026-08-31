/**
 * The flower colours this app knows, and their German names.
 *
 * One list, because there were three: the filter bar, the filter panel and the
 * colour note each carried their own, and the suggestion list carried none at
 * all — so a species the catalogue calls `brown` was shown as "brown" beside a
 * picker offering "braun".
 *
 * The order is the one the pickers show: warm to cool, then the rest.
 */
export const COLOURS: ReadonlyArray<readonly [string, string]> = [
  ['yellow', 'gelb'],
  ['white', 'weiß'],
  ['pink', 'rosa'],
  ['violet', 'violett'],
  ['blue', 'blau'],
  ['red', 'rot'],
  ['orange', 'orange'],
  ['green', 'grün'],
  ['brown', 'braun'],
  ['black', 'schwarz'],
];

const LABELS: Readonly<Record<string, string>> = Object.fromEntries(COLOURS);

/**
 * The German name for a catalogue colour.
 *
 * An unknown value is returned as it stands rather than hidden: the catalogue
 * comes from several sources and may one day say something this list does not
 * cover, and showing it is more use than showing nothing.
 */
export function colourLabel(colour: string): string {
  return LABELS[colour] ?? colour;
}
