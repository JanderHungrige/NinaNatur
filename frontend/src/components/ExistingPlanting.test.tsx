import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ExistingPlanting } from './ExistingPlanting';

function setup(unidentified = 0) {
  const onAdd = vi.fn();
  render(<ExistingPlanting onAdd={onAdd} unidentified={unidentified} busy={false} />);
  return onAdd;
}

describe('ExistingPlanting', () => {
  it('takes a name and a count', () => {
    const onAdd = setup();
    fireEvent.change(screen.getByLabelText(/Pflanze/), { target: { value: 'Bauernhortensie' } });
    fireEvent.change(screen.getByLabelText(/Anzahl/), { target: { value: '3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Eintragen' }));
    expect(onAdd).toHaveBeenCalledWith({ raw_name: 'Bauernhortensie', quantity: 3 });
  });

  it('refuses an empty name rather than sending one', () => {
    const onAdd = setup();
    fireEvent.click(screen.getByRole('button', { name: 'Eintragen' }));
    expect(onAdd).not.toHaveBeenCalled();
  });

  it('says a name may be one we do not know, before the user finds out', () => {
    // The catalogue has no cultivars at all. Someone typing "Bauernhortensie"
    // should not have to discover that by being told they were wrong.
    setup();
    expect(screen.getByText(/auch eintragen, wenn wir sie nicht kennen/i)).toBeDefined();
  });

  it('reports how many plantings could not be identified', () => {
    // A score computed over 4 of 7 plantings must say so.
    setup(3);
    expect(screen.getByText(/3 Pflanzungen/)).toBeDefined();
  });

  it('uses the singular for one', () => {
    setup(1);
    expect(screen.getByText(/1 Pflanzung\b/)).toBeDefined();
  });

  it('says nothing about unidentified plantings when there are none', () => {
    setup(0);
    expect(screen.queryByText(/zugeordnet/)).toBeNull();
  });

  it('clears the field after adding, so the next plant is easy', () => {
    setup();
    const field = screen.getByLabelText(/Pflanze/) as HTMLInputElement;
    fireEvent.change(field, { target: { value: 'Rose' } });
    fireEvent.click(screen.getByRole('button', { name: 'Eintragen' }));
    expect(field.value).toBe('');
  });
});
