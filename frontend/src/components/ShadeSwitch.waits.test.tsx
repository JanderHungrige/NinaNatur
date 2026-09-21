import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { lightMap } from '../testing/gardens';
import { ShadeSwitch } from './ShadeSwitch';

/* The owner's check (2026-09-21): the day's player under the chip that chose
   it, and the panel saying what it waits for (doc 65). */

function show(props: Partial<Parameters<typeof ShadeSwitch>[0]> = {}) {
  render(
    <ShadeSwitch
      map={lightMap()}
      on
      mode="hours"
      month={null}
      onToggle={vi.fn()}
      onMode={vi.fn()}
      onMonth={vi.fn()}
      onRebuild={vi.fn()}
      busy={false}
      {...props}
    />,
  );
}

describe('ShadeSwitch — the day plays where it was chosen', () => {
  it('puts the day’s player directly under the chips, and no longer sends the reader to the dock', () => {
    // Reported: the play button for the day appeared in the dock under the
    // plan, far from the chip that asked for it.
    show({ mode: 'day', dayPlayer: <div data-testid="day-player" /> });
    const modes = screen.getByRole('group', { name: 'Was gezeigt wird' });
    expect(modes.nextElementSibling).toBe(screen.getByTestId('day-player'));
    expect(screen.queryByText(/unten beim Zeitstrahl/)).toBeNull();
  });

  it('shows no player while the heat map is chosen', () => {
    show({ mode: 'hours', dayPlayer: <div data-testid="day-player" /> });
    expect(screen.queryByTestId('day-player')).toBeNull();
  });

  it('says which day it is: the 15th of the Zeitraum’s month', () => {
    show({ mode: 'day' });
    expect(screen.getByText(/15\. des Monats im Zeitraum/)).toBeDefined();
  });
});

describe('ShadeSwitch — saying what it waits for', () => {
  it('says the shade is being computed while it is', () => {
    show({ busy: true, rebuilding: true });
    expect(screen.getByRole('button', { name: 'Wird berechnet…' })).toBeDefined();
    expect(screen.queryByRole('button', { name: 'Schatten neu berechnen' })).toBeNull();
  });

  it('holds the Zeitraum still while the shade is computed', () => {
    // A month picked mid-rebuild was overwritten by the rebuild's season map,
    // and the select went on naming the month (review, 2026-09-21).
    show({ rebuilding: true });
    expect((screen.getByLabelText(/Zeitraum/) as HTMLSelectElement).disabled).toBe(true);
  });

  it('keeps its own name while nothing is computed', () => {
    show({ busy: true });
    expect(screen.getByRole('button', { name: 'Schatten neu berechnen' })).toBeDefined();
  });

  it('says a month’s map is on its way beside the Zeitraum, outside its label', () => {
    show({ monthWorking: true });
    expect(screen.getByText('Karte wird berechnet…')).toBeDefined();
    // Inside the label it would become part of the select's name.
    expect(screen.getByRole('combobox', { name: 'Zeitraum' })).toBeDefined();
  });
});
