import { floweringMonths, monthSpan } from '../suggestions/months';

interface Props {
  start: number | null;
  end: number | null;
}

/**
 * Twelve cells with the flowering months filled (doc 90). A picture of a year
 * means nothing to a screen reader, so it is named with the months in words;
 * and a flowering time nobody recorded is said, not drawn as an empty year
 * (doc 15).
 */
export function MonthStrip({ start, end }: Props) {
  const months = new Set(floweringMonths(start, end));
  if (months.size === 0) return <span className="month-strip__unknown">Blühzeit unbekannt</span>;
  return (
    <span className="month-strip" role="img" aria-label={`Blüte ${monthSpan(start, end)}`}>
      {Array.from({ length: 12 }, (_, index) => (
        <span
          key={index}
          className={
            months.has(index + 1) ? 'month-strip__cell month-strip__cell--on' : 'month-strip__cell'
          }
        />
      ))}
    </span>
  );
}
