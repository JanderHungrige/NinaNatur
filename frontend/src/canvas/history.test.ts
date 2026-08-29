import { describe, expect, it } from 'vitest';

import { type History, canRedo, canUndo, empty, push, redo, undo } from './history';

function of(...states: string[]): History<string> {
  return states.reduce<History<string>>((h, s) => push(h, s), empty('start'));
}

describe('undo', () => {
  it('goes back to the previous state', () => {
    expect(undo(of('a', 'b')).present).toBe('a');
  });

  it('does nothing at the beginning rather than throwing', () => {
    // Ctrl+Z on an untouched drawing is a normal thing for a person to do.
    const h = empty('start');
    expect(undo(h).present).toBe('start');
    expect(canUndo(h)).toBe(false);
  });

  it('is undoable — redo puts it back', () => {
    // An undo that cannot be undone is its own small betrayal.
    expect(redo(undo(of('a'))).present).toBe('a');
  });

  it('drops the redo branch once something new is drawn', () => {
    // Standard, and the alternative is a tree nobody can navigate.
    const branched = push(undo(of('a', 'b')), 'c');
    expect(branched.present).toBe('c');
    expect(canRedo(branched)).toBe(false);
    expect(undo(branched).present).toBe('a');
  });

  it('walks back more than one step', () => {
    expect(undo(undo(of('a', 'b'))).present).toBe('start');
  });

  it('does not grow without limit', () => {
    // A drawing session is long and every vertex is a state.
    let h = empty(0);
    for (let i = 1; i <= 500; i += 1) h = push(h, i);
    expect(h.past.length).toBeLessThanOrEqual(200);
    expect(h.present).toBe(500);
  });

  it('keeps the oldest reachable state usable after trimming', () => {
    let h = empty(0);
    for (let i = 1; i <= 500; i += 1) h = push(h, i);
    while (canUndo(h)) h = undo(h);
    expect(typeof h.present).toBe('number');
  });
});
