import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { SoilLine } from './SoilLine';

describe('SoilLine', () => {
  it('says the garden’s soil in one line once it has been said', () => {
    // Asked once per garden (doc 48) — and then a 448 px form in the sidebar for
    // good. Once answered, the answer is one line.
    render(<SoilLine soilType="loam" moisture="fresh" onSave={vi.fn()} busy={false} />);
    expect(screen.getByText('lehmig, frisch')).toBeDefined();
    expect(screen.queryByLabelText('Boden')).toBeNull();
    expect(screen.getByRole('button', { name: 'Boden ändern' }).getAttribute('aria-expanded')).toBe(
      'false',
    );
  });

  it('opens the question behind ändern, starting from the answer', () => {
    render(<SoilLine soilType="clay" moisture="wet" onSave={vi.fn()} busy={false} />);
    const toggle = screen.getByRole('button', { name: 'Boden ändern' });
    fireEvent.click(toggle);
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect((screen.getByLabelText('Boden') as HTMLSelectElement).value).toBe('clay');
  });

  it('folds the question away again once the answer is saved', () => {
    const onSave = vi.fn();
    render(<SoilLine soilType="loam" moisture="fresh" onSave={onSave} busy={false} />);
    fireEvent.click(screen.getByRole('button', { name: 'Boden ändern' }));
    fireEvent.change(screen.getByLabelText('Feuchte'), { target: { value: 'moist' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ändern' }));
    expect(onSave).toHaveBeenCalledWith('loam', 'moist');
    expect(screen.queryByLabelText('Boden')).toBeNull();
  });

  it('asks outright while the garden has no soil yet', () => {
    render(<SoilLine soilType={null} moisture={null} onSave={vi.fn()} busy={false} />);
    expect(screen.getByLabelText('Boden')).toBeDefined();
    expect(screen.queryByRole('button', { name: 'Boden ändern' })).toBeNull();
  });
});
