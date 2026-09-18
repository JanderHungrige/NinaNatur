import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ElementForm } from './ElementForm';

type Props = Parameters<typeof ElementForm>[0];

/** The form as the details show it: an element with no kind and no name yet. */
function open(props: Partial<Props> = {}) {
  const handlers = {
    onSave: vi.fn(),
    onDelete: vi.fn(),
    onCancel: vi.fn(),
    onFocusTaken: vi.fn(),
  };
  render(
    <ElementForm
      heading="Was ist das?"
      kind="other"
      label={null}
      plantings={0}
      shape="polygon"
      roof="unknown"
      roofSource="user"
      eavesM={null}
      eavesSource={null}
      height={null}
      width={null}
      soilType={null}
      moisture={null}
      heightAboveGround={0}
      busy={false}
      takeFocus={false}
      {...handlers}
      {...props}
    />,
  );
  return handlers;
}

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

/** What a screen reader hears after a field's name: the note under it. */
function noteFor(control: HTMLElement): string | null {
  const id = control.getAttribute('aria-describedby');
  if (id === null) return null;
  return document.getElementById(id)?.textContent ?? null;
}

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
