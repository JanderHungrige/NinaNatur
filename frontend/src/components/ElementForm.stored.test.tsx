import { fireEvent, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { noteFor, open } from '../testing/elementForm';

/* The store can change while the form is open: the laser fills a crown base
   when the light is computed, a survey a height, a roof, the eaves. A field
   that kept what it opened with sent the old value back as the gardener's
   word (review of stage 3, 2026-09-28). */

const save = () => fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));
const rename = (to: string) =>
  fireEvent.change(screen.getByLabelText('Bezeichnung'), { target: { value: to } });

describe('ElementForm — over a store that changes while it is open', () => {
  it('does not send back a crown base the laser filled in the meantime', () => {
    const { onSave, update } = open({ kind: 'tree', height: 12 });
    update({ crownBaseM: 3.2, crownBaseSource: 'measured' });

    const base = screen.getByLabelText('Kronenansatz (m)') as HTMLInputElement;
    expect(base.value).toBe('3.2');
    expect(noteFor(base)).toBe('aus Laserdaten gemessen');
    rename('Linde');
    save();
    expect(onSave).toHaveBeenCalledWith({ kind: 'tree', label: 'Linde' });
  });

  it('does not send back a roof and eaves a survey filled in the meantime', () => {
    const { onSave, update } = open({ kind: 'house', height: 9 });
    update({ roof: 'gable', roofSource: 'surveyed', eavesM: 6.2, eavesSource: 'surveyed' });

    expect((screen.getByLabelText('Dachform') as HTMLSelectElement).value).toBe('gable');
    expect((screen.getByLabelText('Traufhöhe (m)') as HTMLInputElement).value).toBe('6.2');
    rename('Nachbarhaus');
    save();
    expect(onSave).toHaveBeenCalledWith({ kind: 'house', label: 'Nachbarhaus' });
  });

  it('keeps what the gardener typed, though the store changed under it', () => {
    const { onSave, update } = open({ kind: 'house', height: 9 });
    fireEvent.change(screen.getByLabelText('Höhe (m)'), { target: { value: '11' } });
    update({ height: 9.5 });

    expect((screen.getByLabelText('Höhe (m)') as HTMLInputElement).value).toBe('11');
    save();
    expect(onSave).toHaveBeenCalledWith({ kind: 'house', label: '', height: 11 });
  });

  it('keeps the focus in the field it was in', () => {
    const { update } = open({ kind: 'tree', height: 12 });
    const name = screen.getByLabelText('Bezeichnung');
    name.focus();
    update({ crownBaseM: 3.2, crownBaseSource: 'measured' });
    expect(document.activeElement).toBe(name);
  });
});
