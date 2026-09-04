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

  it('says a hand entry answers for every garden here', () => {
    // The wording was "gilt nur für diesen Garten" and it is now the opposite.
    // Somebody typing a colour is contributing to the shared catalogue, and
    // that is worth knowing while they decide what to type.
    render(<ColourNote recorded={null} noted="violet" onNote={vi.fn()} busy={false} />);
    expect(screen.getByText(/für alle Gärten/)).toBeDefined();
    expect((screen.getByLabelText('Blütenfarbe') as HTMLSelectElement).value).toBe('violet');
  });

  it('says a source outranks a hand entry', () => {
    render(<ColourNote recorded="pink" noted={null} onNote={vi.fn()} busy={false} />);
    expect(screen.getByText(/zurückstehen/)).toBeDefined();
    expect((screen.getByLabelText('Blütenfarbe') as HTMLSelectElement).value).toBe('pink');
  });

  it('says so when a source has since overruled the hand entry', () => {
    // The one state that needs explaining: the gardener typed violet, it is
    // still stored, and the plan is drawing blue. Silence here reads as the
    // entry having been lost.
    render(<ColourNote recorded="blue" noted="violet" onNote={vi.fn()} busy={false} />);
    expect(screen.getByText(/inzwischen/)).toBeDefined();
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
