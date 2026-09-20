import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

import type { BloomPalette, GardenOut, LightMap, NinaNaturClient } from '../api/client';
import { App } from '../App';
import { garden, improvements, score, suggestions, timeline } from './gardens';

/*
 * Opening the app in a test (docs 87, 88): the fake client it is handed, and
 * the few ways a flow test finds its way around the workspace.
 */

/** The client the app is handed. Every method the flows reach is here, so a
 *  call to one that is not fails loudly instead of reaching for the network.
 *  An override may add a method the defaults leave out; a test reads it back
 *  as `unknown`, which is all `expect` needs. */
export function fakeClient(
  overrides: Record<string, unknown> = {},
  gardens: Record<string, GardenOut> = {
    tok: garden('tok', 'Testgarten'),
    tok2: garden('tok2', 'Zweitgarten'),
  },
) {
  const defaults = {
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
    // What the garden's numbers rest on (doc 106): nothing, in a fixture.
    sources: vi.fn(async () => []),
    canopies: vi.fn(async () => []),
    bedSuggestions: vi.fn(async () => suggestions()),
    plant: vi.fn(async () => gardens.tok),
    speciesInfo: vi.fn(async () => null),
  };
  return { ...defaults, ...overrides } as typeof defaults & Record<string, unknown>;
}

export type FakeClient = ReturnType<typeof fakeClient>;

/** A matchMedia that answers each query as `matches` decides. */
function mediaAnswering(matches: (query: string) => boolean) {
  return (query: string) => ({
    matches: matches(query), media: query, onchange: null, addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn(),
  });
}

/** jsdom has no matchMedia; the player and the workspace both ask it. Answering
 *  no to everything is a narrow window: the sheet of doc 91. */
export function stubMatchMedia(): void {
  vi.stubGlobal('matchMedia', mediaAnswering(() => false));
}

/** A window at least 66rem wide: the workspace of doc 87, with no sheet. */
export function stubWideLayout(): void {
  vi.stubGlobal('matchMedia', mediaAnswering((query) => query.includes('min-width: 66rem')));
}

export function resetApp(): void {
  vi.unstubAllGlobals();
  window.location.hash = '';
}

export function start(client: FakeClient, hash = ''): void {
  window.location.hash = hash;
  render(<App client={client as unknown as NinaNaturClient} />);
}

/** The garden in the address, opened, with everything about it arrived. */
export async function openWorkspace(client: FakeClient, name = 'Testgarten'): Promise<void> {
  start(client, '#tok');
  await screen.findByText(`${name} geladen.`);
}

/** The details beside the plan. */
export function details(): HTMLElement {
  return screen.getByRole('complementary', { name: 'Details' });
}

/** The heading of the view the details are showing (doc 88). */
export function viewHeading(): HTMLElement | null {
  return details().querySelector<HTMLElement>('h2[data-view-heading]');
}

/** A node of the plan, found by what the plan marks it with. */
export function onPlan(selector: string): SVGElement {
  const found = document.querySelector<SVGElement>(selector);
  if (found === null) throw new Error(`nothing on the plan matches ${selector}`);
  return found;
}
