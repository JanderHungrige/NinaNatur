import type { GardenOut, LightMap } from '../api/client';

/*
 * A sun map for the contact sheet (doc 95): a formula, not a model run. It is
 * there to show the sun layer's two inks over the plan, so it only has to look
 * like a garden's light — full sun in the open, shade north of what stands,
 * roofs answered on the roof.
 */

const CELL_M = 1;
const OPEN_SKY_H = 9.5;
const ROOF_H = 10.5;
/** How far north of a building its shade reaches, per metre of its height. */
const REACH_PER_M = 1.4;

type Obstacle = GardenOut['obstacles'][number];

function boundsOf(points: number[][]): [number, number, number, number] {
  const xs = points.map((p) => p[0] ?? 0);
  const ys = points.map((p) => p[1] ?? 0);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

/** Where something stands, how tall it is, and whether it has a roof. */
type Caster = [number, number, number, number, number, boolean];

/** Hours at one cell: the open sky, less what stands south of it. */
function hoursAt(x: number, y: number, casters: Caster[]): { hours: number; roof: boolean } {
  let hours = OPEN_SKY_H;
  for (const [minX, minY, maxX, maxY, height, roofed] of casters) {
    if (roofed && x >= minX && x <= maxX && y >= minY && y <= maxY) return { hours: ROOF_H, roof: true };
    const reach = REACH_PER_M * height;
    if (x >= minX - 1 && x <= maxX + 1 && y > maxY && y < maxY + reach) {
      hours = Math.min(hours, 2 + (7 * (y - maxY)) / reach);
    }
  }
  return { hours: Math.round(hours * 10) / 10, roof: false };
}

export function sunMapFor(garden: GardenOut): LightMap {
  const all = [...garden.obstacles.flatMap((o) => o.footprint), ...garden.beds.flatMap((b) => b.polygon)];
  const [minX, minY, maxX, maxY] = boundsOf(all);
  const cols = Math.ceil((maxX - minX) / CELL_M) + 2;
  const rows = Math.ceil((maxY - minY) / CELL_M) + 2;
  // Everything standing casts shade; only a building has a roof to answer on.
  const standing = (o: Obstacle) => o.height !== null && o.height > 0;
  const roofed = (o: Obstacle) => o.kind === 'house' || o.kind === 'shed';
  const casters = garden.obstacles.filter(standing).map((o) => {
    const [a, b, c, d] = boundsOf(o.footprint);
    return [a, b, c, d, o.height ?? 0, roofed(o)] as Caster;
  });
  const hours: number[] = [];
  const roof: boolean[] = [];
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const cell = hoursAt(minX - 1 + (col + 0.5) * CELL_M, minY - 1 + (row + 0.5) * CELL_M, casters);
      hours.push(cell.hours);
      roof.push(cell.roof);
    }
  }
  return {
    cell_m: CELL_M, min_x: minX - 1, min_y: minY - 1, cols, rows, hours, roof,
    max_hours: OPEN_SKY_H, computed_at: '2026-09-18T00:00:00+00:00', stale: false,
    morning: hours.map((h) => Math.round(h * 4.5) / 10), misplaced: [],
  };
}
