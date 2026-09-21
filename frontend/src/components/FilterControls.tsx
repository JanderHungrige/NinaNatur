import { COLOURS } from '../colours';
import type { SuggestionFilters } from '../api/client';

interface Props {
  filters: SuggestionFilters;
  onChange: (next: SuggestionFilters) => void;
  /** A request is running. The fields stay in reach and their changes are
   *  ignored: a field disabled under the keyboard's focus throws the focus to
   *  the page (doc 90, as doc 88 rule 11). */
  busy: boolean;
}

const MONTHS = [
  'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
];

/** Bands rather than a slider: nobody wants "höchstens 0,73 m". */
const HEIGHTS: Array<[string, number]> = [
  ['bis 0,3 m', 0.3],
  ['bis 0,5 m', 0.5],
  ['bis 1 m', 1],
  ['bis 2 m', 2],
];


const FORMS: Array<[string, string]> = [
  ['Staude', 'forb'],
  ['Kraut', 'herb'],
  ['Gras', 'graminoid'],
  ['Strauch', 'shrub'],
  ['Halbstrauch', 'subshrub'],
  ['Baum', 'tree'],
];

/**
 * The inputs that set the filters.
 *
 * Split from FilterBar so each stays readable: this is what the user can ask
 * for, FilterBar is what they asked for and what it cost them.
 */
export function FilterControls({ filters, onChange, busy }: Props) {
  /** Choosing the empty option removes the filter rather than setting a blank. */
  const set = <K extends keyof SuggestionFilters>(
    key: K,
    value: SuggestionFilters[K] | undefined,
  ) => {
    // Ignored, the field left as it was: every field here is controlled.
    if (busy) return;
    const next = { ...filters };
    if (value === undefined) {
      delete next[key];
    } else {
      next[key] = value;
    }
    onChange(next);
  };

  return (
    <div className="filter-controls">
      <label>
        Blühmonat
        <select
          value={filters.floweringMonth ?? ''}
          aria-disabled={busy || undefined}
          onChange={(e) =>
            set('floweringMonth', e.target.value === '' ? undefined : Number(e.target.value))
          }
        >
          <option value="">alle</option>
          {MONTHS.map((name, index) => (
            <option key={name} value={index + 1}>
              {name}
            </option>
          ))}
        </select>
      </label>

      <label>
        Höhe
        <select
          value={filters.heightMax ?? ''}
          aria-disabled={busy || undefined}
          onChange={(e) =>
            set('heightMax', e.target.value === '' ? undefined : Number(e.target.value))
          }
        >
          <option value="">beliebig</option>
          {HEIGHTS.map(([label, value]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>

      <label>
        Blütenfarbe
        <select
          value={filters.colour ?? ''}
          aria-disabled={busy || undefined}
          onChange={(e) => set('colour', e.target.value === '' ? undefined : e.target.value)}
        >
          <option value="">beliebig</option>
          {COLOURS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>

      <label>
        Wuchsform
        <select
          value={filters.growthForm ?? ''}
          aria-disabled={busy || undefined}
          onChange={(e) => set('growthForm', e.target.value === '' ? undefined : e.target.value)}
        >
          <option value="">beliebig</option>
          {FORMS.map(([label, value]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>

      {/* Inverted since Wave 6: woody plants are in the list by default. They
          are the catalogue's best forage plants, and the room check — not the
          growth form — decides where they rank. */}
      <label className="filter-controls__toggle">
        <input
          type="checkbox"
          checked={filters.includeTrees === false}
          aria-disabled={busy || undefined}
          onChange={(e) => set('includeTrees', e.target.checked ? false : undefined)}
        />
        Gehölze ausblenden
      </label>

      {/* Owner review #9 (2026-09-21): a bed no longer offers what it is far
          too bright for, because scorch and drought usually kill it. The
          gardener may still want to see them, ranked last. */}
      <label className="filter-controls__toggle">
        <input
          type="checkbox"
          checked={filters.includeLightUnsuitable === true}
          aria-disabled={busy || undefined}
          onChange={(e) => set('includeLightUnsuitable', e.target.checked ? true : undefined)}
        />
        auch Arten zeigen, denen das Licht zu hell ist
      </label>
    </div>
  );
}
