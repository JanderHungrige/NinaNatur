import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { CanopySuggestion } from '../api/client';
import { CanopyBox } from './CanopyBox';

function tree(over: Partial<CanopySuggestion> = {}): CanopySuggestion {
  return { suggestion_id: 1, x: 8, y: -6, radius_m: 4, height_m: 18, ...over };
}

function show(suggestions: CanopySuggestion[], handlers = {}) {
  const props = { onAccept: vi.fn(), onDismiss: vi.fn(), busy: false, ...handlers };
  render(<CanopyBox suggestions={suggestions} {...props} />);
  return props;
}

describe('CanopyBox', () => {
  it('says nothing when there is nothing to suggest', () => {
    const { container } = render(
      <CanopyBox suggestions={[]} onAccept={vi.fn()} onDismiss={vi.fn()} busy={false} />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('says what is actually known about the tree', () => {
    // How tall, how wide, how far. Not a species — no elevation product carries
    // one, and pretending otherwise would be the same lie as an assumed height
    // presented as a measurement.
    show([tree()]);

    expect(screen.getByText(/18,0 m hoch/)).toBeDefined();
    expect(screen.getByText(/8,0 m breit/)).toBeDefined();
    expect(screen.getByText(/10 m entfernt/)).toBeDefined();
  });

  it('says that the species is unknown and what follows from it', () => {
    show([tree()]);
    expect(screen.getByText(/Art weiß niemand/)).toBeDefined();
    expect(screen.getByText(/Laubbaum/)).toBeDefined();
  });

  it('makes refusing exactly as easy as accepting', () => {
    // A list where the "no" is the harder click is a list that gets accepted by
    // exhaustion.
    const { onAccept, onDismiss } = show([tree()]);

    fireEvent.click(screen.getByRole('button', { name: 'Gibt es nicht' }));
    expect(onDismiss).toHaveBeenCalledWith(1);

    fireEvent.click(screen.getByRole('button', { name: 'Eintragen' }));
    expect(onAccept).toHaveBeenCalledWith(1);
  });

  it('offers one row per tree', () => {
    show([tree(), tree({ suggestion_id: 2, height_m: 9 })]);
    expect(screen.getAllByRole('button', { name: 'Eintragen' })).toHaveLength(2);
  });

  it('cannot be clicked twice while a request is in flight', () => {
    const { onAccept } = show([tree()], { busy: true });

    fireEvent.click(screen.getByRole('button', { name: 'Eintragen' }));

    expect(onAccept).not.toHaveBeenCalled();
  });
});
