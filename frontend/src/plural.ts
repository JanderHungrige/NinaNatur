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
export const obstacles = (count: number): string => plural(count, 'Hindernis', 'Hindernisse');
