/**
 * German plurals for the few nouns the UI counts.
 *
 * "1 Beete" is the kind of detail that makes software feel unfinished, and it
 * also ends up inside an aria-label, where a screen reader reads it aloud.
 */
export function plural(count: number, singular: string, pluralForm: string): string {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

export const beds = (count: number): string => plural(count, 'Beet', 'Beete');

/** Insect groups, counted. "1 Schwebfliegenarten" is the same bug as "1 Beete". */
export const insectGroup = (count: number, group: string): string => {
  const forms: Record<string, [string, string]> = {
    bee: ['Wildbienenart', 'Wildbienenarten'],
    butterfly: ['Schmetterlingsart', 'Schmetterlingsarten'],
    hoverfly: ['Schwebfliegenart', 'Schwebfliegenarten'],
  };
  const pair = forms[group];
  return pair === undefined ? `${count} ${group}` : plural(count, pair[0], pair[1]);
};
/** "1 Pflanzung(en)" is the parenthetical dodge around the same bug. */
export const plantings = (count: number): string =>
  plural(count, 'Pflanzung', 'Pflanzungen');

export const birds = (count: number): string =>
  plural(count, 'Vogelart', 'Vogelarten');

export const species = (count: number): string => plural(count, 'Art', 'Arten');

export const obstacles = (count: number): string => plural(count, 'Hindernis', 'Hindernisse');
