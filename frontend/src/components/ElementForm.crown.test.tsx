import { fireEvent, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { noteFor, open } from '../testing/elementForm';

/* Where a crown starts (doc 121): the base a low sun passes under. */

describe('ElementForm — the crown base', () => {
  it.each(['tree', 'shrub'])('asks a %s where the crown starts', (kind) => {
    open({ kind, height: 12 });
    expect(screen.queryByLabelText('Kronenansatz (m)')).not.toBeNull();
  });

  it.each(['hedge', 'house', 'bed'])('does not ask a %s', (kind) => {
    open({ kind, height: 2 });
    expect(screen.queryByLabelText('Kronenansatz (m)')).toBeNull();
  });

  it('does not ask where no crown fits the outline, and says why', () => {
    // A long band casts as a row, from the ground: a base typed there changed
    // nothing (review of stage 3, 2026-09-28).
    open({ kind: 'tree', height: 12, crownFits: false });
    expect(screen.queryByLabelText('Kronenansatz (m)')).toBeNull();
    expect(screen.getByText(/Zu lang oder zu schmal für eine Krone/)).not.toBeNull();
  });

  it('does not ask a hedge drawn as a line that is turned into a tree', () => {
    // The form asked it: whether a crown fits was said of trees only, and the
    // stored kind was a hedge (review of 45eb56a).
    open({ kind: 'hedge', shape: 'line', height: 2, crownFits: false });
    fireEvent.change(screen.getByLabelText('Art'), { target: { value: 'tree' } });
    expect(screen.queryByLabelText('Kronenansatz (m)')).toBeNull();
    expect(screen.getByText(/Zu lang oder zu schmal für eine Krone/)).not.toBeNull();
  });

  it('says what is assumed when nobody gave it: a third of a tree, the ground under a shrub', () => {
    open({ kind: 'tree', height: 12 });
    expect(noteFor(screen.getByLabelText('Kronenansatz (m)'))).toBe(
      'Nicht bekannt: gerechnet wird mit einem Drittel der Höhe, 4,0 m',
    );
  });

  it('says a shrub is reckoned from the ground', () => {
    open({ kind: 'shrub', height: 2 });
    expect(noteFor(screen.getByLabelText('Kronenansatz (m)'))).toBe(
      'Nicht bekannt: gerechnet wird ab dem Boden',
    );
  });

  it('says the laser measured it, and nothing about a base the gardener typed', () => {
    open({ kind: 'tree', height: 18, crownBaseM: 4.2, crownBaseSource: 'measured' });
    open({ kind: 'tree', height: 18, crownBaseM: 4.2, crownBaseSource: 'user' });
    const [measured, typed] = screen.getAllByLabelText('Kronenansatz (m)');
    expect(noteFor(measured!)).toBe('aus Laserdaten gemessen');
    expect(noteFor(typed!)).toBeNull();
  });

  it('sends the base only when it was changed', () => {
    const { onSave } = open({ kind: 'tree', height: 18, crownBaseM: 4.2,
                              crownBaseSource: 'measured' });
    fireEvent.change(screen.getByLabelText('Bezeichnung'), { target: { value: 'Linde' } });
    fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));
    expect(onSave).toHaveBeenLastCalledWith({ kind: 'tree', label: 'Linde' });

    fireEvent.change(screen.getByLabelText('Kronenansatz (m)'), { target: { value: '2.5' } });
    fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));
    expect(onSave).toHaveBeenLastCalledWith({ kind: 'tree', label: 'Linde', crown_base_m: 2.5 });
  });

  it('sends an emptied base as nobody\'s: back on the assumption, not on the ground', () => {
    const { onSave } = open({ kind: 'tree', height: 18, crownBaseM: 4.2,
                              crownBaseSource: 'user' });
    fireEvent.change(screen.getByLabelText('Kronenansatz (m)'), { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));
    expect(onSave).toHaveBeenCalledWith({ kind: 'tree', label: '', crown_base_m: null });
  });
});
