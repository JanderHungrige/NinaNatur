import type { TimelineOut } from '../api/client';
import { plantings } from '../plural';

interface Props {
  timeline: TimelineOut;
  forage: boolean;
  onToggleForage: (forage: boolean) => void;
  busy: boolean;
  /** The month currently filtering the suggestions, if any. */
  selectedMonth?: number | null;
  /**
   * Choosing a month, or clearing it with null. Optional: without it the
   * timeline stays a plain table, which is how it is used read-only elsewhere.
   */
  onSelectMonth?: ((month: number | null) => void) | undefined;
}

const MONTHS = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];

/** Spelled out for anything that gets read aloud — "Mär" is a column width, not a word. */
const FULL_MONTHS = [
  'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
];

function monthName(month: number): string {
  return MONTHS[month - 1] ?? String(month);
}

function fullMonthName(month: number): string {
  return FULL_MONTHS[month - 1] ?? String(month);
}

/** "März bis Mai" — a run of months named the way a person would say it. */
export function describeGap(months: readonly number[]): string {
  const first = months[0];
  const last = months[months.length - 1];
  if (first === undefined || last === undefined) return '';
  return first === last ? monthName(first) : `${monthName(first)} bis ${monthName(last)}`;
}

/**
 * The bloom year.
 *
 * Rendered as a real table with the bars as decoration on top, not as a chart
 * with a caption. Everything a bar shows is also a number in a cell, so nothing
 * here is knowable only by looking at it.
 */
export function BloomTimeline({
  timeline,
  forage,
  onToggleForage,
  busy,
  selectedMonth = null,
  onSelectMonth,
}: Props) {
  const gapMonths = new Set(timeline.gaps.flatMap((gap) => gap.months));

  /** A toggle: the click that says "show me April" is the one used to undo it. */
  const choose = (month: number) => {
    onSelectMonth?.(selectedMonth === month ? null : month);
  };

  return (
    <section className="panel" aria-labelledby="timeline-heading">
      <h2 id="timeline-heading">Blühjahr</h2>

      <div className="checkbox-row">
        <input
          id="forage-mode"
          type="checkbox"
          checked={forage}
          disabled={busy}
          onChange={(event) => onToggleForage(event.target.checked)}
        />
        <label htmlFor="forage-mode">
          Nach Insektenwert gewichten
        </label>
      </div>
      <p className="hint">
        {forage
          ? 'Ein Monat zählt, wenn etwas blüht, das Insekten auch nutzt.'
          : 'Ein Monat zählt, wenn überhaupt etwas blüht — rein optisch.'}
      </p>

      {timeline.is_empty ? (
        <p className="empty">
          Noch nichts gepflanzt. Wähle unten einen Vorschlag für ein Beet aus —
          danach zeigt diese Ansicht, in welchen Monaten dein Garten etwas trägt
          und wo Lücken bleiben.
        </p>
      ) : (
        <>
          <table className="timeline">
            <caption className="sr-only">
              Blühdeckung pro Monat, als Anteil des besten Monats dieses Gartens
            </caption>
            <thead>
              <tr>
                <th scope="col">Monat</th>
                <th scope="col">Anteil</th>
                <th scope="col">Blühend</th>
              </tr>
            </thead>
            <tbody>
              {timeline.months.map((month) => {
                const isGap = gapMonths.has(month.month);
                return (
                  <tr
                    key={month.month}
                    className={
                      [isGap ? 'is-gap' : '', selectedMonth === month.month ? 'is-chosen' : '']
                        .filter(Boolean)
                        .join(' ') || undefined
                    }
                  >
                    <th scope="row">
                      {onSelectMonth === undefined ? (
                        monthName(month.month)
                      ) : (
                        <button
                          type="button"
                          className="month-button"
                          aria-pressed={selectedMonth === month.month}
                          aria-label={`Vorschläge für ${fullMonthName(month.month)}`}
                          disabled={busy}
                          onClick={() => choose(month.month)}
                        >
                          {monthName(month.month)}
                        </button>
                      )}
                    </th>
                    <td>
                      <span
                        className="bar"
                        style={{ '--fill': `${month.coverage * 100}%` } as React.CSSProperties}
                        aria-hidden="true"
                      />
                      {/* The number carries the meaning; the bar only decorates it. */}
                      <span className="bar-value">{Math.round(month.coverage * 100)}%</span>
                      {isGap ? <span className="gap-tag">Lücke</span> : null}
                    </td>
                    <td className="species">
                      {month.species.length > 0 ? month.species.join(', ') : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <p className="hint">
            Anteil jeweils bezogen auf den besten Monat dieses Gartens.
            {timeline.plantings_without_interaction_data > 0 && forage
              ? ` Für ${plantings(timeline.plantings_without_interaction_data)}
                  liegen keine Insektendaten vor — sie zählen einfach mit.`
              : ''}
          </p>

          {timeline.gaps.length > 0 ? (
            <ul className="gap-list">
              {timeline.gaps.map((gap) => (
                <li key={gap.months.join('-')}>
                  {forage ? 'Trachtlücke' : 'Blühlücke'}: {describeGap(gap.months)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="hint">Keine Lücke zwischen März und Oktober.</p>
          )}
        </>
      )}
    </section>
  );
}
