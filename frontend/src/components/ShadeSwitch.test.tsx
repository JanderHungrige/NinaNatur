import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { LightMap } from '../api/client';
import { ShadeSwitch } from './ShadeSwitch';
import { SunMap, bandFor } from './SunMap';

function map(overrides: Partial<LightMap> = {}): LightMap {
  return {
    cell_m: 1,
    min_x: 0,
    min_y: 0,
    cols: 2,
    rows: 2,
    // Dark in the south, bright in the north.
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
      mode="sun"
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

  it('offers both readings of the same number', () => {
    const { onMode } = show();
    fireEvent.click(screen.getByRole('button', { name: 'Schattenstunden' }));
    expect(onMode).toHaveBeenCalledWith('shade');
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

describe('SunMap', () => {
  function draw(mode: 'sun' | 'shade') {
    const { container } = render(
      <svg>
        <SunMap map={map()} mode={mode} />
      </svg>,
    );
    return [...container.querySelectorAll('.sun-map__cell')];
  }

  it('paints the dark places when showing sun', () => {
    // More sun, more transparent: the plan shows through where it is bright and
    // the shade is what stands out.
    const cells = draw('sun');
    const dark = cells.find((c) => c.getAttribute('y') === '-1');
    expect(Number(dark?.getAttribute('opacity'))).toBeGreaterThan(0.4);
  });

  it('paints the bright places when showing shade', () => {
    const cells = draw('shade');
    const bright = cells.find((c) => c.getAttribute('y') === '-2');
    expect(Number(bright?.getAttribute('opacity'))).toBeGreaterThan(0.6);
  });

  it('leaves a cell out entirely rather than drawing nothing visible', () => {
    // A rect at 1% opacity is a node the browser composites for no reason, and
    // a garden is six hundred of them.
    expect(draw('sun').length).toBeLessThan(4);
  });

  it('scales against the garden rather than against a fixed twelve hours', () => {
    // A garden that never gets more than four hours still has a bright end and
    // a dark one, and that difference is the thing worth seeing.
    const { container } = render(
      <svg>
        <SunMap map={map({ hours: [0.5, 0.5, 4.0, 4.0], max_hours: 4.0 })} mode="sun" />
      </svg>,
    );
    const cells = [...container.querySelectorAll('.sun-map__cell')];
    expect(cells.length).toBeGreaterThan(0);
    expect(Number(cells[0]!.getAttribute('opacity'))).toBeGreaterThan(0.4);
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
