import { fireEvent, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { open } from '../testing/elementForm';

describe('ElementForm', () => {
  it('is part of the details, not a dialog over the plan', () => {
    // Doc 88. It was a popover anchored to the shape (doc 51, Wave 15). In the
    // workspace the details beside the plan are where an element is described,
    // so the anchoring, the outside click and Escape have nothing left to close.
    open();
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(screen.getByRole('region', { name: 'Was ist das?' })).toBeDefined();
  });

  it('saves the kind and the label together', () => {
    const { onSave } = open();
    fireEvent.change(screen.getByLabelText('Art'), { target: { value: 'pond' } });
    fireEvent.change(screen.getByLabelText('Bezeichnung'), {
      target: { value: 'Der alte Teich' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));
    expect(onSave).toHaveBeenCalledWith({ kind: 'pond', label: 'Der alte Teich' });
  });

  it('starts from what the element already is', () => {
    open({ kind: 'hedge', label: 'Nachbars Hecke' });
    expect((screen.getByLabelText('Art') as HTMLSelectElement).value).toBe('hedge');
    expect((screen.getByLabelText('Bezeichnung') as HTMLInputElement).value).toBe(
      'Nachbars Hecke',
    );
  });

  it('takes the focus when the element was asked about, and says it has', () => {
    // Right-click, Shift+F10 or the context-menu key on the plan. A question
    // asked from the keyboard has to land where it can be answered.
    const { onFocusTaken } = open({ takeFocus: true });
    expect(document.activeElement).toBe(screen.getByLabelText('Art'));
    expect(onFocusTaken).toHaveBeenCalledTimes(1);
  });

  it('leaves the focus where it was when the element was only selected', () => {
    // Choosing on the plan must not pull the keyboard off the plan.
    const { onFocusTaken } = open();
    expect(document.activeElement).not.toBe(screen.getByLabelText('Art'));
    expect(onFocusTaken).not.toHaveBeenCalled();
  });

  it('keeps its fields and buttons in reach while a request runs, and ignores the buttons', () => {
    // A disabled control cannot hold the focus. Every request would throw the
    // keyboard out of the form, and Shift+F10 on a bed — whose suggestions
    // start loading at that moment — could not put it there at all.
    const { onSave } = open({ busy: true, takeFocus: true });
    const kind = screen.getByLabelText('Art') as HTMLSelectElement;
    expect(kind.disabled).toBe(false);
    expect(document.activeElement).toBe(kind);
    const save = screen.getByRole('button', { name: 'Übernehmen' }) as HTMLButtonElement;
    expect(save.disabled).toBe(false);
    expect(save.getAttribute('aria-disabled')).toBe('true');
    fireEvent.click(save);
    expect(onSave).not.toHaveBeenCalled();
  });

  it('hands the element back on Abbrechen, unsaved', () => {
    const { onCancel, onSave } = open();
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSave).not.toHaveBeenCalled();
  });
});

describe('ElementForm — deleting', () => {
  it('asks before deleting', () => {
    // An element cannot be got back.
    const { onDelete } = open();
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Endgültig löschen' })).toBeDefined();
  });

  it('deletes once confirmed', () => {
    const { onDelete } = open();
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Endgültig löschen' }));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it('says what a planted bed costs before it goes', () => {
    // The same warning re-labelling gives, for the same reason: the plants go
    // with it and nobody should find that out afterwards.
    open({ kind: 'bed', plantings: 7 });
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
    expect(screen.getByRole('alert').textContent).toMatch(/7 Pflanzen/);
  });

  it('says nothing about plants when there are none', () => {
    open({ kind: 'bed', plantings: 0 });
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('lets the question be withdrawn', () => {
    const { onDelete } = open();
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Doch nicht' }));
    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Löschen' })).toBeDefined();
  });
});

describe('ElementForm — the eaves, and why they are asked for', () => {
  it('offers the eaves height on a building', () => {
    // With the ridge it gives the pitch, and the pitch is what makes the north
    // side of a roof darker than the south side. Without it the model assumes
    // three quarters of the way up and says so.
    open({ kind: 'house', height: 9.5 });
    expect(screen.getByLabelText(/Traufhöhe/)).toBeDefined();
  });

  it('does not ask about eaves for something with no roof', () => {
    open({ kind: 'pond' });
    expect(screen.queryByLabelText(/Traufhöhe/)).toBeNull();
  });

  it('sends what was typed', () => {
    const { onSave } = open({ kind: 'house', height: 9.5 });
    fireEvent.change(screen.getByLabelText(/Traufhöhe/), { target: { value: '6.2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ eaves_m: 6.2 }));
  });

  it('sends null when it is cleared, rather than nothing', () => {
    // Null is a value here: it puts the building back on the assumed eaves.
    // Omitting the field would leave the old number in place, and a field that
    // cannot be undone is worse than one that is not offered.
    const { onSave } = open({ kind: 'house', height: 9.5, eavesM: 6.2 });
    fireEvent.change(screen.getByLabelText(/Traufhöhe/), { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ eaves_m: null }));
  });
});
