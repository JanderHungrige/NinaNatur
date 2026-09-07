import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { LightMap } from '../api/client';
import { LEVELS, SunMap, bandFor, hoursAt, washFor } from './SunMap';

function map(overrides: Partial<LightMap> = {}): LightMap {
  return {
    cell_m: 1,
    min_x: 0,
    min_y: 0,
    cols: 2,
    rows: 2,
    // Deep shade in the south, full sun in the north — one on each side of
    // the Halbschatten band the two inks turn on.
    hours: [1.0, 1.0, 7.0, 7.0],
    max_hours: 7.0,
    computed_at: '2026-09-04T10:00:00+00:00',
    stale: false,
    morning: [0.5, 0.5, 3.5, 3.5],
    misplaced: [],
    ...overrides,
  } as LightMap;
}

describe('SunMap — one map, two inks', () => {
  function draw(mode: 'hours' | 'day', over = map()) {
    const { container } = render(
      <svg>
        <SunMap map={over} mode={mode} />
      </svg>,
    );
    return [...container.querySelectorAll('.sun-map__cell')];
  }

  it('paints the sun yellow and the shade grey in the same picture', () => {
    // The whole point of merging the two modes: neither half of the garden is
    // left blank, so the picture can be read without switching.
    const cells = draw('hours');
    const inks = cells.map((c) => c.getAttribute('class'));
    expect(inks.some((c) => c?.includes('sun-map__cell--sun'))).toBe(true);
    expect(inks.some((c) => c?.includes('sun-map__cell--shade'))).toBe(true);
  });

  it('leaves the Halbschatten band unpainted', () => {
    // The hinge the two readings turn on. Painting it in either colour would
    // pick a side that three hours of sun does not.
    expect(draw('hours', map({ hours: [3.0, 3.0, 3.2, 3.2], max_hours: 3.2 }))).toEqual([]);
  });

  it('means the same hours in every garden', () => {
    // It used to scale against the garden's own brightest cell, which was fine
    // for one ink — it only claimed "more than the rest of here". Yellow says
    // sunny, and a yellow meaning 3 h in one garden and 9 h in another would be
    // saying something untrue in one of them.
    const dim = draw('hours', map({ hours: [1.0, 1.0, 4.5, 4.5], max_hours: 4.5 }));
    const bright = draw('hours', map({ hours: [1.0, 1.0, 9.0, 9.0], max_hours: 9.0 }));
    const lit = (cells: Element[]) =>
      cells.filter((c) => c.getAttribute('class')?.includes('--sun'));
    expect(Number(lit(dim)[0]!.getAttribute('opacity')))
      .toBeLessThan(Number(lit(bright)[0]!.getAttribute('opacity')));
  });

  it('still shows the structure of a garden that is dark all over', () => {
    // The courtyard the old relative scale existed for. The ramps are
    // continuous, so its brighter corner survives — in two shades of grey.
    const cells = draw('hours', map({ hours: [0.2, 0.2, 2.0, 2.0], max_hours: 2.0 }));
    const opacities = [...new Set(cells.map((c) => c.getAttribute('opacity')))];
    expect(opacities.length).toBeGreaterThan(1);
  });

  it('keeps only the sunny half under the day, so the shadow is what moves', () => {
    const cells = draw('day');
    expect(cells.length).toBeGreaterThan(0);
    expect(cells.every((c) => c.getAttribute('class')?.includes('--sun'))).toBe(true);
  });

  it('draws nothing where there is no ground to answer for', () => {
    // Null is a cell under a house or a shed. Zero would be a claim about deep
    // shade — true of the footprint, and false of what a plan shows there: a
    // roof, in full sun.
    const roofed = map({ hours: [null, null, 9.0, 9.0], max_hours: 9.0 });
    const cells = draw('hours', roofed);
    expect(cells).toHaveLength(2);
    expect(cells.every((c) => c.getAttribute('class')?.includes('--sun'))).toBe(true);
  });
});

describe('hoursAt', () => {
  it('tells a roof apart from off the map', () => {
    // Two different things to say: outside the grid the map has no opinion, and
    // under a house it has one — that this is not ground.
    const roofed = map({ hours: [null, 1.0, 7.0, 7.0], max_hours: 7.0 });
    expect(hoursAt(roofed, 0.5, 0.5)).toBeNull();
    expect(hoursAt(roofed, 1.5, 1.5)).toBe(7.0);
    expect(hoursAt(roofed, 99, 99)).toBeUndefined();
  });

  it('refuses a point that is not a point', () => {
    // An SVG that has not been laid out measures zero and the viewport
    // arithmetic hands back NaN. NaN passes every bounds test, because every
    // comparison against it is false — so it used to index the array with NaN,
    // get undefined, and report a roof over an open lawn.
    const lit = map({ hours: [7.0, 7.0, 7.0, 7.0], max_hours: 7.0 });
    expect(hoursAt(lit, Number.NaN, 1)).toBeUndefined();
    expect(hoursAt(lit, 1, Number.NaN)).toBeUndefined();
    expect(hoursAt(lit, Number.POSITIVE_INFINITY, 1)).toBeUndefined();
  });
});

describe('washFor', () => {
  it('turns at the band edges the legend names', () => {
    expect(washFor(3.0)).toBeNull();
    expect(washFor(4.5)?.ink).toBe('sun');
    expect(washFor(2.0)?.ink).toBe('shade');
  });

  it('tops out rather than running past the brightest step', () => {
    // 11 h is the last step. A garden that somehow reached 20 would be drawn
    // exactly like one at 11, which is the honest end of the scale.
    expect(washFor(14.0)?.strength).toBe(LEVELS[0]!.strength);
    expect(washFor(11.0)?.strength).toBe(LEVELS[0]!.strength);
  });

  it('keeps its steps apart across the range a garden actually has', () => {
    // The failure this replaced: everything from 6 h upwards was one flat
    // colour, and five sixths of a measured garden sits above 6 h.
    const strengths = [6.5, 8, 9.5, 11.5].map((h) => washFor(h)?.strength);
    expect(new Set(strengths).size).toBe(4);
  });
});

describe('bandFor', () => {
  it('names the hours the way a plant label does', () => {
    expect(bandFor(8)).toBe('volle Sonne');
    expect(bandFor(3)).toBe('Halbschatten');
    expect(bandFor(0.4)).toBe('tiefer Schatten');
  });
});
