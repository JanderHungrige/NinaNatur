import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type {
  BedSuggestions,
  BloomPalette,
  GardenOut,
  ImprovementsOut,
  LightMap,
  NinaNaturClient,
  ScoreOut,
  TimelineOut,
} from './api/client';
import { App } from './App';

function bed(): GardenOut['beds'][number] {
  return {
    bed_id: 1, kind: 'bed', shape: 'polygon', x: 0, y: 0, points: null, width: null,
    constraint_hint: null, name: 'Südbeet', polygon: [[0, 0], [3, 0], [3, 2], [0, 2]],
    soil_type: 'loam', moisture: 'fresh', ellenberg_l: 8, ellenberg_m: 5, ellenberg_n: 5.5,
    ellenberg_r: 6.5, sun_hours: 6.4, slope_deg: null, aspect_deg: null,
    light_computed_at: '2026-08-28T10:00:00+00:00', height_above_ground: 0, label: null,
    plantings: [],
  };
}

function garden(token: string, name: string): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {},
    share_token: token, name, latitude: 51.2564, longitude: 7.1501, created_at: '',
    updated_at: '', beds: [bed()], obstacles: [],
  };
}

const timeline = (): TimelineOut => ({
  mode: 'forage',
  months: Array.from({ length: 12 }, (_, i) => ({ month: i + 1, coverage: 0, species: [] })),
  gaps: [], plantings_total: 0, plantings_without_interaction_data: 0, is_empty: true,
});

const score = (): ScoreOut => ({
  score: 0, by_month: {}, by_species: [], by_group: { bee: 0, butterfly: 0, hoverfly: 0 },
  plantings_total: 0, plantings_without_interaction_data: 0, is_empty: true,
});

const improvements = (): ImprovementsOut => ({ current_score: 0, additions: [], swaps: [] });

const suggestions = (): BedSuggestions => ({
  bed_id: 1, bed_name: 'Südbeet', site_axes: { ellenberg_l: 8 }, total: 1, woody: [],
  woody_total: 0, filters: {},
  items: [{
    taxon_id: 7, canonical_name: 'Sambucus nigra', family: 'Adoxaceae', height_max_m: 6,
    flowering_start_month: 6, flowering_end_month: 7, flower_colour: 'white',
    colour_known: true, bird_partners: null, space_m2: null, fits_bed: true,
    fit: { score: 0.9, axes: {} },
  }],
} as BedSuggestions);

const lightMap = (): LightMap => ({
  cell_m: 1, min_x: 0, min_y: 0, cols: 2, rows: 2, hours: [1, 1, 7, 7],
  roof: [false, false, false, false], max_hours: 7, computed_at: '2026-09-04T10:00:00+00:00',
  stale: false, morning: [0.5, 0.5, 3.5, 3.5], misplaced: [],
} as LightMap);

/** The client the app is handed. Every method the flows reach is here, so a
 *  call to one that is not fails loudly instead of reaching for the network. */
function fakeClient(overrides: Record<string, unknown> = {}) {
  const gardens: Record<string, GardenOut> = {
    tok: garden('tok', 'Testgarten'),
    tok2: garden('tok2', 'Zweitgarten'),
  };
  return {
    version: vi.fn(async () => 'V0.20.test'),
    environment: vi.fn(async () => 'prod'),
    me: vi.fn(async () => null),
    stats: vi.fn(async () => null),
    getGarden: vi.fn(async (token: string) => gardens[token] ?? null),
    timeline: vi.fn(async () => timeline()),
    score: vi.fn(async () => score()),
    improvements: vi.fn(async () => improvements()),
    bloom: vi.fn(async () => ({ beds: [] }) as unknown as BloomPalette),
    lightMap: vi.fn(async (): Promise<LightMap | null> => null),
    terrain: vi.fn(async () => null),
    canopies: vi.fn(async () => []),
    bedSuggestions: vi.fn(async () => suggestions()),
    plant: vi.fn(async () => gardens.tok),
    ...overrides,
  };
}

function start(client: ReturnType<typeof fakeClient>, hash = '') {
  window.location.hash = hash;
  render(<App client={client as unknown as NinaNaturClient} />);
}

async function openWorkspace(client: ReturnType<typeof fakeClient>) {
  start(client, '#tok');
  await screen.findByText('Testgarten geladen.');
}

const bedButton = (): HTMLElement => {
  const found = document.querySelector('.bed-list button');
  if (!(found instanceof HTMLElement)) throw new Error('no bed in the bed list');
  return found;
};

beforeEach(() => {
  // jsdom has no matchMedia; the player and the rail both ask it.
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: false, media: query, onchange: null, addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn(),
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  window.location.hash = '';
});

describe('App — the front door', () => {
  it('asks the client it was given, and opens no workspace', async () => {
    const client = fakeClient();
    start(client);
    await waitFor(() => expect(client.stats).toHaveBeenCalled());
    expect(screen.queryByRole('toolbar')).toBeNull();
    expect(screen.queryByRole('complementary')).toBeNull();
  });
});

describe('App — a garden is a workspace', () => {
  it('opens the garden in the address as one banner, main, details and dock', async () => {
    await openWorkspace(fakeClient());
    for (const role of ['banner', 'main', 'contentinfo'] as const) {
      expect(screen.getAllByRole(role)).toHaveLength(1);
    }
    expect(screen.getAllByRole('complementary', { name: 'Details' })).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 1, name: 'Testgarten' })).toBeDefined();
    expect(screen.getByRole('toolbar', { name: 'Werkzeuge' })).toBeDefined();
  });

  it('asks for a bed’s suggestions when the bed is chosen, and lists them', async () => {
    const client = fakeClient();
    await openWorkspace(client);
    fireEvent.click(bedButton());
    await screen.findByText('Sambucus nigra');
    expect(client.bedSuggestions).toHaveBeenCalledWith('tok', 1, {});
  });

  it('puts an armed tool down on Escape, and the rail shows it', async () => {
    await openWorkspace(fakeClient());
    const rect = screen.getByRole('button', { name: 'Rechteck' });
    fireEvent.click(rect);
    expect(rect.getAttribute('aria-pressed')).toBe('true');
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(rect.getAttribute('aria-pressed')).toBe('false');
  });

  it('has nothing to undo when a garden has just opened', async () => {
    await openWorkspace(fakeClient());
    const undo = screen.getByRole('button', { name: 'Letzte Änderung rückgängig' });
    expect((undo as HTMLButtonElement).disabled).toBe(true);
  });

  it('keeps the shade switch off until there is a map to show', async () => {
    await openWorkspace(fakeClient());
    expect((screen.getByRole('button', { name: 'Sonne & Schatten' }) as HTMLButtonElement).disabled)
      .toBe(true);
  });

  it('puts the map over the plan from the header once there is one', async () => {
    await openWorkspace(fakeClient({ lightMap: vi.fn(async () => lightMap()) }));
    const shade = screen.getByRole('button', { name: 'Sonne & Schatten' });
    await waitFor(() => expect((shade as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(shade);
    expect(shade.getAttribute('aria-pressed')).toBe('true');
  });
});

describe('App — one garden does not leak into the next', () => {
  it('starts a garden opened after another with nothing selected', async () => {
    // A bed chosen in one garden stayed chosen in the next: going home reset
    // eight of thirty-six pieces of state, and opening a garden reset none.
    const client = fakeClient();
    await openWorkspace(client);
    fireEvent.click(bedButton());
    await screen.findByText('Sambucus nigra');

    fireEvent.click(screen.getByRole('button', { name: 'Zur Startseite' }));
    fireEvent.change(await screen.findByLabelText('Garten-ID'), { target: { value: 'tok2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Garten öffnen' }));
    await screen.findByText('Zweitgarten geladen.');

    expect(bedButton().getAttribute('aria-pressed')).toBe('false');
    expect(screen.queryByText('Sambucus nigra')).toBeNull();
  });
});

describe('App — failures are said', () => {
  it('reports a failed planting and keeps it until it is closed', async () => {
    const client = fakeClient({
      plant: vi.fn(async () => {
        throw new Error('Netzwerkfehler');
      }),
    });
    await openWorkspace(client);
    fireEvent.click(bedButton());
    fireEvent.click(await screen.findByRole('button', { name: 'Pflanzen' }));
    await screen.findByText('Pflanzen fehlgeschlagen: Netzwerkfehler');
    expect(screen.getByRole('button', { name: 'Schließen' })).toBeDefined();
  });
});
