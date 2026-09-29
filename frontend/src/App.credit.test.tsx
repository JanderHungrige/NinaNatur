import { screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
  details, fakeClient, openWorkspace, resetApp, stubMatchMedia, stubWideLayout,
} from './testing/appFixtures';
import { garden, shed } from './testing/gardens';

/* Where the plan's credits stand (doc 98). The owner, 2026-09-29: on a phone
   the credits go all the way down. Three lines of his under the drawing took
   the room the plan has least of. The map keeps a mark in the drawing's
   corner, where OpenStreetMap's guidelines ask for its credit to be seen
   without scrolling, and its full line joins his at the foot of the details
   (the owner chose both). */

const STYLE = /Zeichenstil nach Draft Sketch/;
const MAP = 'Karte: © OpenStreetMap-Mitwirkende';

const credits = (within: Element | null) =>
  [...(within?.querySelectorAll('.plan-credit') ?? [])].map((line) => line.textContent ?? '');
const plan = () => document.querySelector('.workspace__plan');
const corner = () => screen.queryByRole('link', { name: '© OpenStreetMap' });
const street = shed({ obstacle_id: 7, kind: 'street', label: 'Hauptstraße', height: null });
const mapped = () => fakeClient({}, { tok: garden('tok', 'Testgarten', { obstacles: [street] }) });

beforeEach(() => {
  try {
    window.localStorage.clear();
  } catch {
    // A browser that refuses storage draws the default style, Draft Sketch.
  }
});
afterEach(resetApp);

describe('App — the credits on a phone', () => {
  beforeEach(stubMatchMedia);

  it('closes the details with his credit, and leaves none of it under the plan', async () => {
    await openWorkspace(fakeClient());

    expect(credits(plan())).toEqual([]);
    const last = details().lastElementChild;
    expect(last?.classList.contains('plan-credit')).toBe(true);
    expect(last?.textContent).toMatch(STYLE);
    expect(corner()).toBeNull();
  });

  it('marks the map in the drawing\'s corner and gives its full line at the foot of the details', async () => {
    await openWorkspace(mapped());

    expect(credits(plan())).toEqual([]);
    expect(document.querySelector('.canvas-stage')?.contains(corner())).toBe(true);
    const [his, map] = credits(details()).slice(-2);
    expect(his).toMatch(STYLE);
    expect(map).toBe(MAP);
    expect(details().lastElementChild?.textContent).toBe(MAP);
  });
});

describe('App — the credits on a wide window', () => {
  beforeEach(stubWideLayout);

  it('gives both captions beneath the plan, none in the details, and marks no corner', async () => {
    await openWorkspace(mapped());

    const below = credits(plan());
    expect(below).toHaveLength(2);
    expect(below[0]).toMatch(STYLE);
    expect(below[1]).toBe(MAP);
    expect(credits(details())).toEqual([]);
    expect(corner()).toBeNull();
  });
});
