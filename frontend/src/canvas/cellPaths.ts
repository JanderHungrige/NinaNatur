/**
 * A grid of cells drawn as a few paths, one per kind of cell.
 *
 * The sun map and the relief used to be one `<rect>` per cell. That was
 * thousands of nodes for a garden made from the map, all rebuilt and repainted
 * on every pan (the owner's check, 2026-09-21, #11), and a finer grid (#6)
 * would have multiplied them by four for every halving of the cell. As paths,
 * the count is the number of kinds, whatever the grid. A run of equal cells
 * along a row is one rectangle, which keeps each path short.
 */

export interface CellGrid {
  min_x: number;
  min_y: number;
  cell_m: number;
  cols: number;
  rows: number;
}

/** To the millimetre, like the rest of the plan's path data. */
const mm = (value: number): string => String(Math.round(value * 1000) / 1000);

/**
 * One path's `d` per key, in the order the keys are first met. `keyOf` gives a
 * cell's kind, or null to leave it out. Rows run northwards and the plan draws
 * y downwards, so a row's top edge on screen is its northern edge.
 */
export function cellPaths<K extends string>(
  grid: CellGrid,
  keyOf: (index: number) => K | null,
): Map<K, string> {
  const parts = new Map<K, string[]>();
  const { min_x: minX, min_y: minY, cell_m: cell, cols, rows } = grid;
  const keys = Array.from({ length: rows * cols }, (_, index) => keyOf(index));
  for (let row = 0; row < rows; row += 1) {
    const top = mm(-(minY + (row + 1) * cell));
    let col = 0;
    while (col < cols) {
      const key = keys[row * cols + col] ?? null;
      let end = col + 1;
      while (end < cols && (keys[row * cols + end] ?? null) === key) end += 1;
      if (key !== null) {
        const width = mm((end - col) * cell);
        const d = `M${mm(minX + col * cell)},${top}h${width}v${mm(cell)}h-${width}z`;
        const list = parts.get(key);
        if (list === undefined) parts.set(key, [d]);
        else list.push(d);
      }
      col = end;
    }
  }
  return new Map([...parts].map(([key, list]) => [key, list.join('')]));
}
