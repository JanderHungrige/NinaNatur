import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { KINDS } from '../kinds';
import { type EditableObject, ObjectEditor } from './ObjectEditor';

const BED: EditableObject = {
  id: 1,
  objectKind: 'bed',
  name: 'Südbeet',
  label: null,
  height: null,
  heightAboveGround: 0,
  plantings: 0,
  shape: 'polygon',
  width: null,
  soilType: null,
  moisture: null,
};

const TREE: EditableObject = {
  id: 2,
  objectKind: 'tree',
  name: null,
  label: 'Die Buche vom Nachbarn',
  height: 8,
  heightAboveGround: 0,
  plantings: 0,
  shape: 'polygon',
  width: null,
  soilType: null,
  moisture: null,
};

describe('ObjectEditor', () => {
  it('names the object it is editing', () => {
    render(<ObjectEditor object={BED} onSave={vi.fn()} onClose={vi.fn()} busy={false} />);
    expect(screen.getByRole('heading', { name: /Südbeet/ })).toBeDefined();
  });

  it('offers a raised height for a bed, because that changes its light', () => {
    const onSave = vi.fn();
    render(<ObjectEditor object={BED} onSave={onSave} onClose={vi.fn()} busy={false} />);
    fireEvent.change(screen.getByLabelText(/Höhe über Grund/), { target: { value: '0.8' } });
    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    // The kind rides along on every save now: the panel is "what is this".
    expect(onSave).toHaveBeenCalledWith({
      kind: 'bed',
      height_above_ground: 0.8,
      label: '',
    });
  });

  it('does not offer a raised height for an obstacle', () => {
    render(<ObjectEditor object={TREE} onSave={vi.fn()} onClose={vi.fn()} busy={false} />);
    expect(screen.queryByLabelText(/Höhe über Grund/)).toBeNull();
  });

  it('offers every kind the vocabulary knows, and nothing else', () => {
    // Asserted against the shared list rather than a hand-copied one. The
    // hand-copied version of this test demanded 'building' long after the
    // server had split it into house and shed, so it guarded the drift.
    render(<ObjectEditor object={TREE} onSave={vi.fn()} onClose={vi.fn()} busy={false} />);
    const select = screen.getByLabelText('Art') as HTMLSelectElement;
    expect([...select.options].map((o) => o.value)).toEqual(KINDS.map((k) => k.kind));
  });

  it('fills in the height a kind usually has when the kind changes', () => {
    // Choosing "Hecke" should answer a question, not ask one.
    render(<ObjectEditor object={TREE} onSave={vi.fn()} onClose={vi.fn()} busy={false} />);
    fireEvent.change(screen.getByLabelText('Art'), { target: { value: 'fence' } });
    expect((screen.getByLabelText(/^Höhe/) as HTMLInputElement).value).toBe('1.2');
  });

  it('does not overwrite a height the user typed themselves', () => {
    // A default is a starting value, not a constraint.
    render(<ObjectEditor object={TREE} onSave={vi.fn()} onClose={vi.fn()} busy={false} />);
    fireEvent.change(screen.getByLabelText(/^Höhe/), { target: { value: '4.5' } });
    fireEvent.change(screen.getByLabelText('Art'), { target: { value: 'hedge' } });
    expect((screen.getByLabelText(/^Höhe/) as HTMLInputElement).value).toBe('4.5');
  });

  it('keeps the free label free', () => {
    const onSave = vi.fn();
    render(<ObjectEditor object={TREE} onSave={onSave} onClose={vi.fn()} busy={false} />);
    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(onSave.mock.calls[0]?.[0]).toMatchObject({ label: 'Die Buche vom Nachbarn' });
  });

  it('closes without saving', () => {
    const onSave = vi.fn();
    const onClose = vi.fn();
    render(<ObjectEditor object={TREE} onSave={onSave} onClose={onClose} busy={false} />);
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
    expect(onClose).toHaveBeenCalled();
    expect(onSave).not.toHaveBeenCalled();
  });
});

describe('ObjectEditor — saying what a thing is', () => {
  it('always offers the kind, bed or not', () => {
    // Wave 10 hid it on a bed, which is the old two-table split showing
    // through: a bed could not become anything else.
    render(<ObjectEditor object={BED} onSave={vi.fn()} onClose={vi.fn()} busy={false} />);
    expect(screen.getByLabelText('Art')).toBeDefined();
  });

  it('warns before a re-label costs the plants standing in it', () => {
    const planted: EditableObject = { ...BED, plantings: 7 };
    render(
      <ObjectEditor object={planted} onSave={vi.fn()} onClose={vi.fn()} busy={false} />,
    );
    fireEvent.change(screen.getByLabelText('Art'), { target: { value: 'pond' } });
    expect(screen.getByRole('alert').textContent).toMatch(/7 Pflanzen/);
    expect(screen.getByRole('alert').textContent).toMatch(/Teich/);
  });

  it('says nothing when the element stays a bed', () => {
    const planted: EditableObject = { ...BED, plantings: 7 };
    render(
      <ObjectEditor object={planted} onSave={vi.fn()} onClose={vi.fn()} busy={false} />,
    );
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('says nothing when there was nothing to lose', () => {
    render(<ObjectEditor object={BED} onSave={vi.fn()} onClose={vi.fn()} busy={false} />);
    fireEvent.change(screen.getByLabelText('Art'), { target: { value: 'pond' } });
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('sends the kind even when it did not change', () => {
    // The panel is "what is this". A save that omitted an unchanged kind would
    // work until the day somebody relied on it.
    const onSave = vi.fn();
    render(<ObjectEditor object={BED} onSave={onSave} onClose={vi.fn()} busy={false} />);
    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(onSave.mock.calls[0]?.[0]).toMatchObject({ kind: 'bed' });
  });
});
