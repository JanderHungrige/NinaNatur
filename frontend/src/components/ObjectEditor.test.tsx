import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { KINDS } from '../kinds';
import { ObjectEditor } from './ObjectEditor';

const BED = {
  kind: 'bed' as const,
  id: 1,
  name: 'Südbeet',
  label: null,
  heightAboveGround: 0,
};

const TREE = {
  kind: 'obstacle' as const,
  id: 2,
  objectKind: 'tree',
  label: 'Die Buche vom Nachbarn',
  height: 8,
  width: 6,
  depth: null,
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
    expect(onSave).toHaveBeenCalledWith({ height_above_ground: 0.8, label: '' });
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
