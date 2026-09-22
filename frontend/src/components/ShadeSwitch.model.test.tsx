import { cleanup, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { lightMap } from '../testing/gardens';
import { ShadeSwitch } from './ShadeSwitch';

/*
 * Every model change raises a version that enters the map's signature (Wave
 * 26, doc 117), and the page names the model that drew the map it shows — so a
 * number that moved can be traced to the model that moved it.
 */

function show(model: string, stale = false) {
  render(
    <ShadeSwitch map={{ ...lightMap(), model, stale }} on mode="hours" month={null}
                 onToggle={vi.fn()} onMode={vi.fn()} onMonth={vi.fn()} onRebuild={vi.fn()}
                 busy={false} />,
  );
}

describe('ShadeSwitch — which model drew the map', () => {
  it('names it beside the date', () => {
    show('26.2');
    expect(screen.getByText(/Berechnet am .*, Lichtmodell 26\.2\./)).toBeDefined();
  });

  it('says nothing it does not know about a map from before models had a version', () => {
    show('');
    expect(screen.getByText(/Berechnet am/)).toBeDefined();
    expect(screen.queryByText(/Lichtmodell/)).toBeNull();
  });

  it('names it on a map that is out of date too, which is when it matters most', () => {
    // A map an older model drew reads stale by design (doc 117).
    show('26.2', true);
    expect(screen.getByText(/Nicht mehr aktuell.*Gezeichnet mit Lichtmodell 26\.2\./)).toBeDefined();
    cleanup();
    show('', true);
    expect(screen.getByText(/Gezeichnet mit einem älteren Lichtmodell\./)).toBeDefined();
  });
});
