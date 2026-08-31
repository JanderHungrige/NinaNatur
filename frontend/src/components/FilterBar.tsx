import type { SuggestionFilters } from '../api/client';
import { colourLabel } from '../colours';

/** How one active filter divided the catalogue, as the API reported it. */
export interface FilterCounts {
  matched: number;
  unknown: number;
  excluded: number;
}

interface Props {
  filters: SuggestionFilters;
  counts: Record<string, FilterCounts>;
  onChange: (next: SuggestionFilters) => void;
}

const MONTHS = [
  'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
];


const FORMS: Record<string, string> = {
  forb: 'Staude',
  herb: 'Kraut',
  graminoid: 'Gras',
  shrub: 'Strauch',
  subshrub: 'Halbstrauch',
  tree: 'Baum',
};

/** German decimal comma — "0.5 m" is not how a height is written here. */
function metres(value: number): string {
  return `${value.toLocaleString('de-DE')} m`;
}

interface Chip {
  /** Which reported filter this chip corresponds to, for its coverage note. */
  key: string;
  label: string;
  /** The filter fields this chip owns, cleared together when it is removed. */
  clears: Array<keyof SuggestionFilters>;
}

function chipsFor(filters: SuggestionFilters): Chip[] {
  const chips: Chip[] = [];
  if (filters.heightMax !== undefined) {
    chips.push({
      key: 'height',
      label: `höchstens ${metres(filters.heightMax)}`,
      clears: ['heightMax'],
    });
  }
  if (filters.floweringMonth !== undefined) {
    chips.push({
      key: 'flowering_month',
      label: `blüht im ${MONTHS[filters.floweringMonth - 1] ?? filters.floweringMonth}`,
      clears: ['floweringMonth'],
    });
  }
  if (filters.growthForm !== undefined) {
    chips.push({
      key: 'growth_form',
      label: FORMS[filters.growthForm] ?? filters.growthForm,
      clears: ['growthForm'],
    });
  }
  if (filters.colour !== undefined) {
    chips.push({
      key: 'colour',
      label: colourLabel(filters.colour),
      clears: ['colour'],
    });
  }
  if (filters.includeTrees === false) {
    chips.push({ key: 'trees', label: 'ohne Gehölze', clears: ['includeTrees'] });
  }
  return chips;
}

/**
 * The active filters, each one visible and removable.
 *
 * Filters here are not a neutral narrowing of a complete catalogue. Height is
 * recorded for 44% of German species and flower colour for 6.6%, and coverage
 * tracks how well-studied a plant is — so a filter that hides what it could not
 * judge quietly favours the familiar. Every chip therefore carries what the
 * filter did to the species it had no data for.
 */
export function FilterBar({ filters, counts, onChange }: Props) {
  const chips = chipsFor(filters);

  if (chips.length === 0) {
    return (
      <p className="hint filter-bar__empty">
        Keine Filter aktiv — alle passenden Arten werden gezeigt.
      </p>
    );
  }

  const remove = (chip: Chip) => {
    const next = { ...filters };
    for (const field of chip.clears) delete next[field];
    // The unknown toggle belongs to the filters, not to the user: with no
    // filter left there is nothing for it to include.
    if (chipsFor(next).length === 0) delete next.includeUnknown;
    onChange(next);
  };

  const unknown = chips
    .map((chip) => ({ chip, count: counts[chip.key]?.unknown ?? 0 }))
    .filter((entry) => entry.count > 0);
  const worst = unknown.sort((a, b) => b.count - a.count)[0];

  return (
    <div className="filter-bar">
      <ul className="filter-bar__chips">
        {chips.map((chip) => (
          <li key={chip.key} className="chip">
            <span>{chip.label}</span>
            <button
              type="button"
              className="chip__remove"
              aria-label={`Filter „${chip.label}“ entfernen`}
              onClick={() => remove(chip)}
            >
              ×
            </button>
          </li>
        ))}
        <li>
          <button
            type="button"
            className="link-button"
            aria-label="Alle Filter entfernen"
            onClick={() => onChange({})}
          >
            alle entfernen
          </button>
        </li>
      </ul>

      {worst !== undefined && (
        <p className="hint filter-bar__coverage">
          {worst.count.toLocaleString('de-DE')} Arten ohne Angabe zu „{worst.chip.label}“ sind
          nicht in der Liste.{' '}
          <label className="filter-bar__unknown">
            <input
              type="checkbox"
              checked={filters.includeUnknown === true}
              onChange={(event) =>
                onChange(
                  event.target.checked
                    ? { ...filters, includeUnknown: true }
                    : (({ includeUnknown: _drop, ...rest }) => rest)(filters),
                )
              }
            />
            ohne Angabe mitzeigen
          </label>
        </p>
      )}

      {filters.colour !== undefined && (
        <p className="hint">
          Farbe ist nur für wenige Arten erfasst, deshalb sortiert sie die Liste, statt sie
          zu kürzen.
        </p>
      )}
    </div>
  );
}
