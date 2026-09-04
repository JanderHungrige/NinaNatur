import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useUndoShortcut, useUndoStack } from './useUndoStack';

describe('useUndoStack', () => {
  it('takes the last action back first', async () => {
    const done: string[] = [];
    const { result } = renderHook(() => useUndoStack());

    act(() => {
      result.current.remember({ label: 'Rechteck', undo: async () => { done.push('rect'); } });
      result.current.remember({ label: 'Verschieben', undo: async () => { done.push('move'); } });
    });
    await act(async () => { await result.current.undo(); });
    await act(async () => { await result.current.undo(); });

    expect(done).toEqual(['move', 'rect']);
    expect(result.current.depth).toBe(0);
  });

  it('does nothing, quietly, when there is nothing to undo', async () => {
    const { result } = renderHook(() => useUndoStack());
    let entry: unknown = 'unset';
    await act(async () => { entry = await result.current.undo(); });
    expect(entry).toBeNull();
  });

  it('keeps the stack bounded', () => {
    // Every entry is a closure holding a garden. An unbounded stack keeps every
    // one this session ever saw.
    const { result } = renderHook(() => useUndoStack());
    act(() => {
      for (let i = 0; i < 25; i += 1) {
        result.current.remember({ label: `${i}`, undo: async () => undefined });
      }
    });
    expect(result.current.depth).toBe(10);
  });

  it('forgets everything when the garden changes', () => {
    // The inverses are calls against one garden. Replayed against another they
    // would edit an element that is not there, or worse, one that is.
    const { result } = renderHook(() => useUndoStack());
    act(() => {
      result.current.remember({ label: 'x', undo: async () => undefined });
      result.current.forget();
    });
    expect(result.current.depth).toBe(0);
  });
});

describe('useUndoShortcut', () => {
  function press(key: string, init: KeyboardEventInit = {}, target?: HTMLElement) {
    const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init });
    (target ?? window).dispatchEvent(event);
    return event;
  }

  it('fires on Ctrl+Z and on Cmd+Z', () => {
    const undo = vi.fn();
    renderHook(() => useUndoShortcut(undo, true));

    press('z', { ctrlKey: true });
    press('z', { metaKey: true });

    expect(undo).toHaveBeenCalledTimes(2);
  });

  it('leaves a text field to the browser', () => {
    // Somebody mid-word in a label field pressing Ctrl+Z means the word, not
    // the rectangle they drew a minute ago.
    const undo = vi.fn();
    renderHook(() => useUndoShortcut(undo, true));
    const input = document.createElement('input');
    document.body.append(input);

    press('z', { ctrlKey: true }, input);

    expect(undo).not.toHaveBeenCalled();
    input.remove();
  });

  it('ignores Ctrl+Shift+Z, which means redo', () => {
    const undo = vi.fn();
    renderHook(() => useUndoShortcut(undo, true));
    press('z', { ctrlKey: true, shiftKey: true });
    expect(undo).not.toHaveBeenCalled();
  });

  it('is silent while no garden is open', () => {
    const undo = vi.fn();
    renderHook(() => useUndoShortcut(undo, false));
    press('z', { ctrlKey: true });
    expect(undo).not.toHaveBeenCalled();
  });
});
