import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ColourNote } from './ColourNote';

describe('ColourNote', () => {
  it('says when the catalogue has nothing, which is the usual case', () => {
    // 590 of 8,939 species carry a colour.
    render(<ColourNote recorded={null} noted={null} onNote={vi.fn()} busy={false} />);
    expect(screen.getByText(/keine Farbe erfasst/)).toBeDefined();
  });

  it('records what was chosen', () => {
    const onNote = vi.fn();
    render(<ColourNote recorded={null} noted={null} onNote={onNote} busy={false} />);
    fireEvent.change(screen.getByLabelText('Blütenfarbe'), { target: { value: 'violet' } });
    expect(onNote).toHaveBeenCalledWith('violet');
  });

  it('says an entry is the gardener’s own and local', () => {
    // It never reaches the catalogue, and saying so is the difference between
    // a note and a claim about the species.
    render(<ColourNote recorded={null} noted="violet" onNote={vi.fn()} busy={false} />);
    expect(screen.getByText(/nur für diesen Garten/)).toBeDefined();
    expect((screen.getByLabelText('Blütenfarbe') as HTMLSelectElement).value).toBe('violet');
  });

  it('offers to override what the catalogue says, for a cultivar', () => {
    render(<ColourNote recorded="pink" noted={null} onNote={vi.fn()} busy={false} />);
    expect(screen.getByText(/Sorte/)).toBeDefined();
    expect((screen.getByLabelText('Blütenfarbe') as HTMLSelectElement).value).toBe('pink');
  });

  it('can be taken back', () => {
    const onNote = vi.fn();
    render(<ColourNote recorded={null} noted="violet" onNote={onNote} busy={false} />);
    fireEvent.change(screen.getByLabelText('Blütenfarbe'), { target: { value: '' } });
    expect(onNote).toHaveBeenCalledWith(null);
  });

  it('offers only colours the plan can draw', () => {
    render(<ColourNote recorded={null} noted={null} onNote={vi.fn()} busy={false} />);
    const options = [...(screen.getByLabelText('Blütenfarbe') as HTMLSelectElement).options];
    // Ten swatches plus the "not recorded" entry.
    expect(options).toHaveLength(11);
  });
});
