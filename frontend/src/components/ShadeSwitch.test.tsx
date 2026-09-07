import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { LightMap } from '../api/client';
import { ShadeSwitch } from './ShadeSwitch';
import { LEVELS, bandFor } from './SunMap';

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
    roof: [false, false, false, false],
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
  const onMonth = vi.fn();
  const onRebuild = vi.fn();
  render(
    <ShadeSwitch
      map={map()}
      on
      mode="hours"
      month={null}
      onToggle={onToggle}
      onMode={onMode}
      onMonth={onMonth}
      onRebuild={onRebuild}
      busy={false}
      {...props}
    />,
  );
  return { onToggle, onMode, onMonth, onRebuild };
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

  it('gives the legend one row per step the map draws', () => {
    // The map used to reach full yellow at 6 h, where the plant-label
    // convention stops caring — and five sixths of a real garden sits above
    // that, in one flat colour. The legend is what makes the extra steps
    // readable rather than merely present.
    show();
    const swatches = [...document.querySelectorAll('.shade-switch__swatch')];
    expect(swatches).toHaveLength(LEVELS.length);
    expect(swatches.map((s) => s.getAttribute('data-ink'))).toEqual(
      LEVELS.map((l) => l.ink ?? 'none'),
    );
    // Strictly increasing yellow: the point of having steps at all.
    const yellows = swatches
      .filter((s) => s.getAttribute('data-ink') === 'sun')
      .map((s) => Number((s as HTMLElement).style.opacity));
    expect(yellows).toEqual([...yellows].sort((a, b) => b - a));
    expect(new Set(yellows).size).toBe(yellows.length);
  });

  it('keeps the band names agreeing with the naming convention', () => {
    // Two tables, one truth. `bandFor` mirrors the server's SUN_HOUR_BANDS and
    // the legend reads its names off the map's steps; a name that drifted
    // would label the map with something the server never said.
    for (const level of LEVELS) {
      if (level.name !== undefined) {
        expect(bandFor(level.from)).toBe(level.name);
      }
    }
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

  it('offers a month instead of the whole season', () => {
    // A garden with a house to its south is a different garden in April and in
    // July, and the season average describes neither.
    const { onMonth } = show();
    fireEvent.change(screen.getByLabelText(/Zeitraum/), { target: { value: '3' } });
    expect(onMonth).toHaveBeenCalledWith(3);
  });

  it('can be put back to the whole season', () => {
    const { onMonth } = show({ month: 6 });
    fireEvent.change(screen.getByLabelText(/Zeitraum/), { target: { value: 'season' } });
    expect(onMonth).toHaveBeenCalledWith(null);
  });

  it('offers no winter, because the light model has none', () => {
    show();
    const options = [...screen.getByLabelText(/Zeitraum/).querySelectorAll('option')];
    expect(options.map((o) => o.value)).toEqual(
      ['season', '3', '4', '5', '6', '7', '8', '9', '10'],
    );
  });

  it('says there is nothing to show for an empty garden', () => {
    show({ map: null });
    expect(screen.getByText(/Noch nichts gezeichnet/)).toBeDefined();
    expect(screen.queryByRole('button', { name: 'Sonnenstunden' })).toBeNull();
    expect((screen.getByRole('checkbox') as HTMLInputElement).disabled).toBe(true);
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
