import { describe, expect, it } from 'vitest';

import { KINDS } from '../kinds';
import { SHEET_GARDENS, SHEET_MONTH, coloursFor } from './gardens';

/*
 * The contact sheet's gardens (doc 95). They are what the plan is looked at
 * through, so they have to hold everything the plan can draw — and be the shape
 * the API sends, or the sheet shows a plan the app never renders.
 */

const garden = (name: string) => {
  const found = SHEET_GARDENS.find((g) => g.id === name);
  if (found === undefined) throw new Error(`no sheet garden ${name}`);
  return found.garden;
};

describe('the sheet gardens', () => {
  it('are the three the sheet is laid out by', () => {
    expect(SHEET_GARDENS.map((g) => g.id)).toEqual(['small', 'farmyard', 'city']);
  });

  it('draw every kind there is in the small one alone', () => {
    const small = garden('small');
    const drawn = new Set([...small.obstacles.map((o) => o.kind), ...small.beds.map((b) => b.kind)]);
    expect([...drawn].sort()).toEqual(KINDS.map((k) => k.kind).sort());
  });

  it('have one ground each', () => {
    for (const { garden: g } of SHEET_GARDENS) {
      expect(g.obstacles.filter((o) => o.kind === 'garden')).toHaveLength(1);
    }
  });

  it('put at least a hundred elements in the city, the performance case', () => {
    const city = garden('city');
    expect(city.obstacles.length + city.beds.length).toBeGreaterThanOrEqual(100);
  });

  it('are the shape the API sends: an outline is its points moved to where it stands', () => {
    for (const { garden: g } of SHEET_GARDENS) {
      for (const o of g.obstacles) {
        expect(o.points).not.toBeNull();
        const moved = (o.points ?? []).map(([x, y]) => [x! + o.x, y! + o.y]);
        expect(o.footprint).toEqual(moved);
      }
    }
  });

  it('never reuse an id inside one garden', () => {
    for (const { garden: g } of SHEET_GARDENS) {
      const ids = [...g.obstacles.map((o) => o.obstacle_id), ...g.beds.map((b) => b.bed_id)];
      expect(new Set(ids).size).toBe(ids.length);
      const plantings = g.beds.flatMap((b) => b.plantings.map((p) => p.planting_id));
      expect(new Set(plantings).size).toBe(plantings.length);
    }
  });

  it('have something in flower in the month the sheet shows', () => {
    for (const { garden: g } of SHEET_GARDENS) {
      const flowering = coloursFor(g).filter((c) => c.colour !== null && c.months.includes(SHEET_MONTH));
      expect(flowering.length).toBeGreaterThan(0);
    }
  });
});
