import { fireEvent, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { noteFor, notesFor, open } from '../testing/elementForm';

/* Where the roof came from (doc 93) and which way its ridge runs (doc 94). */

describe('ElementForm — only what changed is sent (doc 93)', () => {
  const surveyed = {
    kind: 'house', height: 9.5, roof: 'gable', roofSource: 'surveyed', eavesM: 6.2,
    eavesSource: 'surveyed',
  } as const;

  it('sends no height, roof or eaves when only the name changed', () => {
    // It sent all three. The server takes a height in the body as the user's
    // word on it, so renaming a surveyed house made its height an entry — and
    // no refresh measured it again.
    const { onSave } = open(surveyed);
    fireEvent.change(screen.getByLabelText('Bezeichnung'), { target: { value: 'Nachbarhaus' } });
    fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));
    expect(onSave).toHaveBeenCalledWith({ kind: 'house', label: 'Nachbarhaus' });
  });

  it('sends the height that was changed and leaves the rest', () => {
    const { onSave } = open(surveyed);
    fireEvent.change(screen.getByLabelText('Höhe (m)'), { target: { value: '11' } });
    fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));
    expect(onSave).toHaveBeenCalledWith({ kind: 'house', label: '', height: 11 });
  });

  it('sends a roof shape that was changed', () => {
    const { onSave } = open(surveyed);
    fireEvent.change(screen.getByLabelText('Dachform'), { target: { value: 'hip' } });
    fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));
    expect(onSave).toHaveBeenCalledWith({ kind: 'house', label: '', roof: 'hip' });
  });
});

describe('ElementForm — where the roof came from (doc 93)', () => {
  it('says the eaves were surveyed', () => {
    open({ kind: 'house', height: 9.5, eavesM: 6.2, eavesSource: 'surveyed' });
    expect(noteFor(screen.getByLabelText(/Traufhöhe/))).toBe('amtlich vermessen');
  });

  it('says the eaves came from the storey count', () => {
    open({ kind: 'house', height: 9, eavesM: 6, eavesSource: 'osm_levels' });
    expect(noteFor(screen.getByLabelText(/Traufhöhe/))).toBe('aus Geschosszahl geschätzt');
  });

  it('says what is assumed when nobody gave the eaves', () => {
    open({ kind: 'house', height: 9 });
    expect(noteFor(screen.getByLabelText(/Traufhöhe/))).toBe(
      'Nicht bekannt: gerechnet wird mit drei Vierteln der Firsthöhe, 6,8 m',
    );
  });

  it('says nothing about eaves the gardener typed', () => {
    // The same number, once surveyed and once typed: only the survey is named.
    open({ kind: 'house', height: 9, eavesM: 5, eavesSource: 'surveyed' });
    open({ kind: 'house', height: 9, eavesM: 5, eavesSource: 'user' });
    const [surveyedEaves, typedEaves] = screen.getAllByLabelText(/Traufhöhe/);
    expect(noteFor(surveyedEaves!)).toBe('amtlich vermessen');
    expect(noteFor(typedEaves!)).toBeNull();
  });

  it('owns up to eaves stored before anybody kept track', () => {
    open({ kind: 'house', height: 9, eavesM: 6.2, eavesSource: null });
    expect(noteFor(screen.getByLabelText(/Traufhöhe/))).toBe('Herkunft nicht vermerkt');
  });

  it('drops the note once the value is typed over: it is the gardener\'s now', () => {
    open({ kind: 'house', height: 9.5, eavesM: 6.2, eavesSource: 'surveyed' });
    expect(noteFor(screen.getByLabelText(/Traufhöhe/))).toBe('amtlich vermessen');
    fireEvent.change(screen.getByLabelText(/Traufhöhe/), { target: { value: '5.5' } });
    expect(noteFor(screen.getByLabelText(/Traufhöhe/))).toBeNull();
  });

  it('says where the roof shape came from', () => {
    open({ kind: 'house', height: 9, roof: 'gable', roofSource: 'surveyed' });
    expect(noteFor(screen.getByLabelText('Dachform'))).toBe('amtlich vermessen');
  });

  it('says an imported shape is OpenStreetMap\'s', () => {
    open({ kind: 'house', height: 9, roof: 'hip', roofSource: 'osm' });
    expect(noteFor(screen.getByLabelText('Dachform'))).toBe('aus OpenStreetMap');
  });

  it('says nothing about a shape nobody has given', () => {
    // "Weiß nicht" from OpenStreetMap is not a shape OpenStreetMap gave.
    open({ kind: 'house', height: 9, roof: 'hip', roofSource: 'osm' });
    open({ kind: 'house', height: 9, roof: 'unknown', roofSource: 'osm' });
    const [given, notGiven] = screen.getAllByLabelText('Dachform');
    expect(noteFor(given!)).toBe('aus OpenStreetMap');
    expect(noteFor(notGiven!)).toBeNull();
  });
});

describe('ElementForm — which way the ridge runs (doc 94)', () => {
  it('says which way a surveyed ridge runs, and the pitch it gives', () => {
    open({ kind: 'house', height: 9, roof: 'gable', roofSource: 'surveyed', roofFallDeg: 0,
           roofPitchDeg: 38.2 });
    expect(notesFor(screen.getByLabelText('Dachform'))).toEqual([
      'amtlich vermessen',
      'First Ost–West (amtlich vermessen) · Neigung 38°',
    ]);
  });

  it('says the ridge is assumed where nobody has measured it', () => {
    open({ kind: 'house', height: 9, roof: 'gable', roofSource: 'user', roofPitchDeg: 27.6 });
    expect(notesFor(screen.getByLabelText('Dachform'))).toEqual([
      'First entlang der längeren Seite (angenommen) · Neigung 28°',
    ]);
  });

  it('says which way a pent roof falls', () => {
    open({ kind: 'shed', height: 3, roof: 'pent', roofSource: 'surveyed', roofFallDeg: 0,
           roofPitchDeg: 12 });
    expect(notesFor(screen.getByLabelText('Dachform'))).toContain(
      'Fällt nach Norden (amtlich vermessen) · Neigung 12°',
    );
  });

  it('says nothing about a ridge on a flat roof', () => {
    // Beside a gable surveyed the same way, which does have one.
    open({ kind: 'house', height: 9, roof: 'gable', roofSource: 'surveyed', roofFallDeg: 0,
           roofPitchDeg: 30 });
    open({ kind: 'house', height: 9, roof: 'flat', roofSource: 'surveyed' });
    const [gable, flat] = screen.getAllByLabelText('Dachform');
    expect(notesFor(gable!)).toHaveLength(2);
    expect(notesFor(flat!)).toEqual(['amtlich vermessen']);
  });

  it('drops the ridge once another shape is chosen: it described the old one', () => {
    open({ kind: 'house', height: 9, roof: 'gable', roofSource: 'surveyed', roofFallDeg: 0,
           roofPitchDeg: 38 });
    expect(notesFor(screen.getByLabelText('Dachform'))).toHaveLength(2);
    fireEvent.change(screen.getByLabelText('Dachform'), { target: { value: 'hip' } });
    expect(notesFor(screen.getByLabelText('Dachform'))).toEqual([]);
  });
});
