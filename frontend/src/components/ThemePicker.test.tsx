import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ThemePicker } from './ThemePicker';

/* The switch between plan styles (doc 100). */

const both = [{ id: 'technisch', label: 'Technisch' }, { id: 'draft-sketch', label: 'Draft Sketch' }];

describe('the plan style picker', () => {
  it('names every style on offer and marks the one being drawn', () => {
    render(<ThemePicker options={both} chosen="draft-sketch" onChoose={() => {}} />);
    const radio = (name: string) => screen.getByRole('radio', { name }) as HTMLInputElement;
    expect(radio('Draft Sketch').checked).toBe(true);
    expect(radio('Technisch').checked).toBe(false);
  });

  it('hands the choice on when one is picked', () => {
    const chose = vi.fn();
    render(<ThemePicker options={both} chosen="technisch" onChoose={chose} />);
    fireEvent.click(screen.getByRole('radio', { name: 'Draft Sketch' }));
    expect(chose).toHaveBeenCalledWith('draft-sketch');
  });

  it('is not drawn at all where there is nothing to choose between', () => {
    const { container } = render(
      <ThemePicker options={[both[0]!]} chosen="technisch" onChoose={() => {}} />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('says so, rather than lying, when high contrast has taken the choice away', () => {
    render(<ThemePicker options={both} chosen="technisch" onChoose={() => {}} overridden />);
    expect((screen.getByRole('radio', { name: 'Draft Sketch' }) as HTMLInputElement).disabled)
      .toBe(true);
    // Said out loud, not merely greyed out.
    expect(screen.getByText(/hohem Kontrast/).textContent).toContain('technische');
  });
});
