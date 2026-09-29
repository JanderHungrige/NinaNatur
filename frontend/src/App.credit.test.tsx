import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
  details, fakeClient, openWorkspace, resetApp, stubMatchMedia, stubWideLayout,
} from './testing/appFixtures';
import { garden, shed } from './testing/gardens';

/* Where the plan's credits stand (doc 98). The owner, 2026-09-29: on a phone
   his credit goes all the way down. Three lines of it under the drawing took
   the room the plan has least of, so it closes the details there. The map's
   line stays under the plan, where ODbL asks for it. */

const STYLE = /Zeichenstil nach Draft Sketch/;
const MAP = 'Karte: © OpenStreetMap-Mitwirkende';

const credits = (within: Element | null) =>
  [...(within?.querySelectorAll('.plan-credit') ?? [])].map((line) => line.textContent ?? '');
const plan = () => document.querySelector('.workspace__plan');

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

    expect(credits(plan()).some((line) => STYLE.test(line))).toBe(false);
    const last = details().lastElementChild;
    expect(last?.classList.contains('plan-credit')).toBe(true);
    expect(last?.textContent).toMatch(STYLE);
  });

  it('keeps the map\'s line under the plan that draws the map', async () => {
    const street = shed({ obstacle_id: 7, kind: 'street', label: 'Hauptstraße', height: null });
    await openWorkspace(fakeClient({}, { tok: garden('tok', 'Testgarten', { obstacles: [street] }) }));

    expect(credits(plan())).toEqual([MAP]);
    expect(credits(details())).not.toContain(MAP);
  });
});

describe('App — the credits on a wide window', () => {
  beforeEach(stubWideLayout);

  it('gives his credit beneath the plan, and none in the details', async () => {
    await openWorkspace(fakeClient());

    expect(credits(plan()).some((line) => STYLE.test(line))).toBe(true);
    expect(credits(details())).toEqual([]);
  });
});
