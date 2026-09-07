import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { LightMap } from '../api/client';
import { ShadeSwitch } from './ShadeSwitch';
import { SunMap, bandFor, washFor } from './SunMap';

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

function show(props: Record<string, unknown> = {}) {
  const onToggle = vi.fn();
  const onMode = vi.fn();
  const onRebuild = vi.fn();
  render(
    <ShadeSwitch
      map={map()}
      on
      mode="hours"
      onToggle={onToggle}
      onMode={onMode}
      onRebuild={onRebuild}
      busy={false}
      {...props}
    />,
  );
  return { onToggle, onMode, onRebuild };
}

describe('ShadeSwitch', () => {
  it('puts the numbers in the legend', () => {
    // "Darker means less sun" is not a reading. Somebody buying a plant labelled
    // Halbschatten needs the figure they can compare against the label.
    show();
    // In the legend specifically: the word now appears in the morning-sun note
    // as well, which is the sentence that explains why the split matters.
    const legend = screen.getByRole('list');
    expect(legend.textContent).toContain('Halbschatten');
    expect(screen.getByText(/2\.5–4 h/)).toBeDefined();
  });

  it('names the brightest spot in the garden', () => {
    show();
    expect(screen.getByText(/7\.0 h am Tag/)).toBeDefined();
  });

  it('does not ask the reader to pick a direction any more', () => {
    // One number, one map. Two modes that each left half the garden blank meant
    // reading the whole picture by switching back and forth and remembering.
    show();
    expect(screen.queryByRole('button', { name: 'Schattenstunden' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Sonnenstunden' })).toBeDefined();
  });

  it("paints the legend with the map's own function", () => {
    // A legend maintained separately drifts, and this one is the only thing
    // that says what the two inks mean.
    show();
    const swatches = [...document.querySelectorAll('.shade-switch__swatch')];
    expect(swatches.map((s) => s.getAttribute('data-ink'))).toEqual([
      'sun', 'sun', 'none', 'shade', 'shade',
    ]);
  });

  it('says when the map was computed', () => {
    // The map is stored because it is expensive, so it can be out of date. One
    // that is quietly out of date is worse than one that admits it.
    show();
    expect(screen.getByText(/Berechnet am/)).toBeDefined();
  });

  it('says so when it is stale rather than showing an old date', () => {
    show({ map: map({ stale: true }) });
    expect(screen.getByText(/nicht neu gerechnet/)).toBeDefined();
  });

  it('can be told to rebuild', () => {
    const { onRebuild } = show();
    fireEvent.click(screen.getByRole('button', { name: 'Schatten neu berechnen' }));
    expect(onRebuild).toHaveBeenCalled();
  });

  it('says there is nothing to show for an empty garden', () => {
    show({ map: null });
    expect(screen.getByText(/Noch nichts gezeichnet/)).toBeDefined();
    expect(screen.queryByRole('button', { name: 'Sonnenstunden' })).toBeNull();
    expect((screen.getByRole('checkbox') as HTMLInputElement).disabled).toBe(true);
  });
});

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

  it('leaves a cell out entirely rather than drawing nothing visible', () => {
    // A rect at 1% opacity is a node the browser composites for no reason, and
    // a garden is six hundred of them.
    expect(draw('hours', map({ hours: [4.01, 4.01, 4.01, 4.01], max_hours: 4.01 })))
      .toEqual([]);
  });
});

describe('washFor', () => {
  it('turns at the band edges the legend names', () => {
    expect(washFor(3.0)).toBeNull();
    expect(washFor(4.5)?.ink).toBe('sun');
    expect(washFor(2.0)?.ink).toBe('shade');
  });

  it('saturates rather than running past full strength', () => {
    expect(washFor(14.0)?.strength).toBe(1);
    expect(washFor(0)?.strength).toBe(1);
  });
});

describe('ShadeSwitch — what is standing wrong', () => {
  it('names a plant that is too dark and says how dark', () => {
    show({
      map: map({
        misplaced: [{
          planting_id: 1, bed_id: 2, taxon_id: 3, name: 'Sonnenkraut',
          wants: 8, gets: 3, sun_hours: 1.2, problem: 'too_dark',
        }],
      }),
    });

    expect(screen.getByText('Sonnenkraut')).toBeDefined();
    expect(screen.getByText(/zu dunkel: 1.2 h/)).toBeDefined();
  });

  it('names the forgotten direction too', () => {
    // A fern in the open is as misplaced as a sedum under a hedge, and only
    // one of the two ever gets talked about.
    show({
      map: map({
        misplaced: [{
          planting_id: 1, bed_id: 2, taxon_id: 3, name: 'Wurmfarn',
          wants: 3, gets: 8, sun_hours: 11.4, problem: 'too_bright',
        }],
      }),
    });

    expect(screen.getByText(/zu hell: 11.4 h/)).toBeDefined();
  });

  it('says it is a hint rather than an objection', () => {
    show({
      map: map({
        misplaced: [{
          planting_id: 1, bed_id: 2, taxon_id: 3, name: 'X',
          wants: 8, gets: 3, sun_hours: 1.0, problem: 'too_dark',
        }],
      }),
    });

    expect(screen.getByText(/kein Einwand/)).toBeDefined();
  });

  it('says nothing at all when nothing is misplaced', () => {
    show();
    expect(screen.queryByText(/falschen Licht/)).toBeNull();
  });

  it('says how much of the sun comes before noon', () => {
    // Afternoon sun is hotter and harsher, and a total cannot say which four
    // hours a spot gets.
    show();
    expect(screen.getByText(/Davon vormittags: 50 %/)).toBeDefined();
  });

  it('leaves the split out on a grid computed before it existed', () => {
    show({ map: map({ morning: [] }) });
    expect(screen.queryByText(/Davon vormittags/)).toBeNull();
  });
});

describe('bandFor', () => {
  it('names the hours the way a plant label does', () => {
    expect(bandFor(8)).toBe('volle Sonne');
    expect(bandFor(3)).toBe('Halbschatten');
    expect(bandFor(0.4)).toBe('tiefer Schatten');
  });
});

describe('ShadeSwitch — where the ground came from', () => {
  const ground = {
    cell_m: 1, min_x: 0, min_y: 0, cols: 2, rows: 2, relief: [0.5, 0.5, 0.5, 0.5],
    lowest: 252.8, highest: 278.6, source: 'Nordrhein-Westfalen',
    licence: 'dl-de/zero-2-0', attribution: '© Geobasis NRW', vertical_step_m: 0.01,
  };

  it('names the source, because a height without its credit is used outside its licence', () => {
    show({ terrain: ground });
    expect(screen.getByText(/© Geobasis NRW/)).toBeDefined();
  });

  it('says what the ground does, in metres', () => {
    show({ terrain: ground });
    expect(screen.getByText(/253–279 m ü\. NHN/)).toBeDefined();
    expect(screen.getByText(/25\.8 m Unterschied/)).toBeDefined();
  });

  it('states the accuracy rather than implying there is none to state', () => {
    show({ terrain: ground });
    expect(screen.getByText(/± 0,3 m/)).toBeDefined();
  });

  it('warns when the service only measures whole metres', () => {
    // Baden-Württemberg's INSPIRE coverage. A 20 m garden on a 3 % slope rises
    // 0.6 m, which whole metres cannot see at all.
    show({ terrain: { ...ground, vertical_step_m: 1.0, source: 'Baden-Württemberg' } });
    expect(screen.getByText(/ganzen Metern/)).toBeDefined();
  });

  it('says plainly when there is no ground to be had', () => {
    // Nine Bundesländer. Flat is what every garden was before Wave 17, and
    // being quiet about it is what this whole wave exists to stop.
    show({ terrain: null });
    expect(screen.getByText(/keine Höhendaten vor/)).toBeDefined();
    expect(screen.getByText(/ebenem Gelände/)).toBeDefined();
  });

  it('says nothing at all when the ground was never asked about', () => {
    show();
    expect(screen.queryByText(/Höhendaten|ü\. NHN/)).toBeNull();
  });
});

describe('ShadeSwitch — recomputing is now something you ask for', () => {
  it('puts the rebuild button at the top, where the panel starts', () => {
    // Nothing recomputes on a write any more, so the button is not a footnote
    // under the legend: it is the first thing in the panel.
    show();
    const panel = screen.getByRole('region', { name: 'Sonne und Schatten' });
    const rebuild = screen.getByRole('button', { name: 'Schatten neu berechnen' });
    const modes = screen.getByRole('button', { name: 'Sonnenstunden' });
    const order = rebuild.compareDocumentPosition(modes);
    expect(panel.contains(rebuild)).toBe(true);
    // eslint-disable-next-line no-bitwise
    expect(order & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('says why somebody would press it', () => {
    show();
    expect(screen.getByText(/neue Beete|neu angelegt|Objekte/)).toBeDefined();
  });

  it('offers the button before anything has ever been computed', () => {
    // The regression this whole change could have introduced: with no recompute
    // on a write, a fresh garden has no map at all — and the old panel hid the
    // only button that could make one.
    show({ map: null });
    expect(screen.getByRole('button', { name: 'Schatten neu berechnen' })).toBeDefined();
  });
});

describe('ShadeSwitch — the map and the day are separate choices', () => {
  it('offers the day as its own choice, beside the heat map', () => {
    const { onMode } = show();
    fireEvent.click(screen.getByRole('button', { name: 'Tagesverlauf' }));
    expect(onMode).toHaveBeenCalledWith('day');
  });

  it('says what the day mode shows, because it is the only one with shadows', () => {
    show({ mode: 'day' });
    expect(screen.getByText(/Objektschatten|wandern/)).toBeDefined();
  });
});
