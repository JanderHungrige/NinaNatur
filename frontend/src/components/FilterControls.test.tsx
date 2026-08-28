import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { SuggestionFilters } from '../api/client';
import { FilterControls } from './FilterControls';

function setup(filters: SuggestionFilters = {}) {
  const onChange = vi.fn();
  render(<FilterControls filters={filters} onChange={onChange} disabled={false} />);
  return onChange;
}

describe('FilterControls', () => {
  it('sends the month as a number, not the label', () => {
    const onChange = setup();
    fireEvent.change(screen.getByLabelText('Blühmonat'), { target: { value: '6' } });
    expect(onChange).toHaveBeenCalledWith({ floweringMonth: 6 });
  });

  it('removes a filter rather than setting it blank', () => {
    // An empty string would be sent as a filter value and match nothing.
    const onChange = setup({ colour: 'yellow' });
    fireEvent.change(screen.getByLabelText('Blütenfarbe'), { target: { value: '' } });
    expect(onChange).toHaveBeenCalledWith({});
  });

  it('keeps the other filters when one changes', () => {
    const onChange = setup({ colour: 'yellow' });
    fireEvent.change(screen.getByLabelText('Höhe'), { target: { value: '0.5' } });
    expect(onChange).toHaveBeenCalledWith({ colour: 'yellow', heightMax: 0.5 });
  });

  it('drops the woody toggle instead of sending false', () => {
    const onChange = setup({ includeTrees: true });
    fireEvent.click(screen.getByRole('checkbox', { name: /Gehölze mitzeigen/ }));
    expect(onChange).toHaveBeenCalledWith({});
  });

  it('shows the current filters as the selected options', () => {
    setup({ floweringMonth: 3, heightMax: 1, growthForm: 'shrub' });
    expect((screen.getByLabelText('Blühmonat') as HTMLSelectElement).value).toBe('3');
    expect((screen.getByLabelText('Höhe') as HTMLSelectElement).value).toBe('1');
    expect((screen.getByLabelText('Wuchsform') as HTMLSelectElement).value).toBe('shrub');
  });
});
