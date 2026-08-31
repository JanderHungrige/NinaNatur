import type { GardenOut } from '../api/client';
import { labelOf } from '../kinds';

interface Props {
  garden: GardenOut;
  selectedId: number | null;
  onSelect: (id: number) => void;
}

interface Row {
  id: number;
  kind: string;
  label: string | null;
  /** What it covers, so two identical-sounding rows can still be told apart. */
  area: number;
}

/** Shoelace, on the footprint the server already computed. */
export function areaOf(points: number[][]): number {
  let sum = 0;
  for (let i = 0; i < points.length; i += 1) {
    const a = points[i]!;
    const b = points[(i + 1) % points.length]!;
    sum += a[0]! * b[1]! - b[0]! * a[1]!;
  }
  return Math.abs(sum) / 2;
}

/**
 * Everything drawn, as a list.
 *
 * The answer to shapes lying on top of each other. Draw order helps with two of
 * them and nothing helps with three — but a list reaches any of them, including
 * the one entirely underneath another.
 *
 * Selecting a row is the same selection the plan makes, so the editor beside it
 * is where the naming happens. A second editing surface would be a second place
 * for the two to disagree about what is selected.
 */
export function ElementList({ garden, selectedId, onSelect }: Props) {
  const rows: Row[] = [
    ...garden.beds.map((b) => ({
      id: b.bed_id,
      kind: 'bed',
      label: b.label ?? b.name,
      area: areaOf(b.polygon),
    })),
    ...garden.obstacles.map((o) => ({
      id: o.obstacle_id,
      kind: o.kind,
      label: o.label,
      area: areaOf(o.footprint),
    })),
  ];

  return (
    <section className="panel element-list" aria-labelledby="elements-heading">
      <h2 id="elements-heading">Gezeichnete Objekte</h2>
      {rows.length === 0 ? (
        <p className="hint">
          Noch nichts gezeichnet. Wähle oben eine Form und zieh sie im Plan auf.
        </p>
      ) : (
        <ul className="element-list__rows">
          {rows.map((row) => (
            <li key={row.id}>
              <button
                type="button"
                className="element-list__row"
                aria-pressed={row.id === selectedId}
                onClick={() => onSelect(row.id)}
              >
                <span className="element-list__what">{labelOf(row.kind)}</span>
                {row.label !== null && row.label !== '' && (
                  <span className="element-list__label">{row.label}</span>
                )}
                <span className="element-list__area">
                  {row.area.toFixed(1).replace('.', ',')} m²
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
