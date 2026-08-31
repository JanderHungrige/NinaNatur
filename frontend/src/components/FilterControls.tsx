import { COLOURS } from '../colours';
import type { SuggestionFilters } from '../api/client';

interface Props {
  filters: SuggestionFilters;
  onChange: (next: SuggestionFilters) => void;
  disabled: boolean;
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
export function FilterControls({ filters, onChange, disabled }: Props) {
  /** Choosing the empty option removes the filter rather than setting a blank. */
  const set = <K extends keyof SuggestionFilters>(
    key: K,
    value: SuggestionFilters[K] | undefined,
  ) => {
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
          disabled={disabled}
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
          disabled={disabled}
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
          disabled={disabled}
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
          disabled={disabled}
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
          disabled={disabled}
          onChange={(e) => set('includeTrees', e.target.checked ? false : undefined)}
        />
        Gehölze ausblenden
      </label>
    </div>
  );
}
