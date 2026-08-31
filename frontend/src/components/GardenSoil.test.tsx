import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { GardenSoil } from './GardenSoil';

describe('GardenSoil', () => {
  it('asks once, in words a hand in the soil can answer', () => {
    render(<GardenSoil soilType={null} moisture={null} onSave={vi.fn()} busy={false} />);
    const soil = screen.getByLabelText('Boden') as HTMLSelectElement;
    // "rieselt, trocknet schnell" is answerable in the garden; a soil
    // classification is not.
    expect([...soil.options].map((o) => o.textContent).join(' ')).toMatch(/rieselt/);
  });

  it('saves what was chosen', () => {
    const onSave = vi.fn();
    render(<GardenSoil soilType={null} moisture={null} onSave={onSave} busy={false} />);
    fireEvent.change(screen.getByLabelText('Boden'), { target: { value: 'clay' } });
    fireEvent.change(screen.getByLabelText('Feuchte'), { target: { value: 'moist' } });
    fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));
    expect(onSave).toHaveBeenCalledWith('clay', 'moist');
  });

  it('says the answer is a starting point once it has one', () => {
    // The difference matters: before, it is a question; after, it is a default
    // that individual beds may leave behind.
    render(
      <GardenSoil soilType="loam" moisture="fresh" onSave={vi.fn()} busy={false} />,
    );
    expect(screen.getByRole('button', { name: 'Ändern' })).toBeDefined();
    expect(screen.getByText(/Ausgangswert/)).toBeDefined();
  });

  it('offers a way to look the soil up rather than guessing it for the user', () => {
    render(<GardenSoil soilType={null} moisture={null} onSave={vi.fn()} busy={false} />);
    const link = screen.getByRole('link', { name: /nachschlagen/ });
    expect(link.getAttribute('rel')).toContain('noopener');
    expect(link.getAttribute('target')).toBe('_blank');
  });

  it('starts from what the garden already said', () => {
    render(<GardenSoil soilType="sand" moisture="dry" onSave={vi.fn()} busy={false} />);
    expect((screen.getByLabelText('Boden') as HTMLSelectElement).value).toBe('sand');
    expect((screen.getByLabelText('Feuchte') as HTMLSelectElement).value).toBe('dry');
  });
});
