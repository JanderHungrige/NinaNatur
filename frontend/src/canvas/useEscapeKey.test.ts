import { fireEvent, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useEscapeKey } from './useEscapeKey';

const added: HTMLElement[] = [];

function inPage(tag: 'input' | 'textarea' | 'select' | 'button' | 'div', type?: string): HTMLElement {
  const element = document.createElement(tag);
  if (type !== undefined) element.setAttribute('type', type);
  document.body.append(element);
  added.push(element);
  return element;
}

afterEach(() => {
  for (const element of added.splice(0)) element.remove();
});

describe('useEscapeKey', () => {
  it('answers Escape', () => {
    const onEscape = vi.fn();
    renderHook(() => useEscapeKey(onEscape));
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onEscape).toHaveBeenCalledTimes(1);
  });

  it('ignores every other key', () => {
    const onEscape = vi.fn();
    renderHook(() => useEscapeKey(onEscape));
    fireEvent.keyDown(window, { key: 'Enter' });
    expect(onEscape).not.toHaveBeenCalled();
  });

  it('leaves Escape typed into a text field to that field', () => {
    // Doc 88. A name half typed into the details must not vanish together with
    // the selection it belongs to.
    const onEscape = vi.fn();
    renderHook(() => useEscapeKey(onEscape));
    const editable = inPage('div');
    editable.setAttribute('contenteditable', 'true');
    for (const typed of [inPage('input'), inPage('input', 'number'), inPage('textarea'), editable]) {
      fireEvent.keyDown(typed, { key: 'Escape' });
    }
    expect(onEscape).not.toHaveBeenCalled();
  });

  it('still answers Escape from a select, a checkbox or a button', () => {
    const onEscape = vi.fn();
    renderHook(() => useEscapeKey(onEscape));
    fireEvent.keyDown(inPage('select'), { key: 'Escape' });
    fireEvent.keyDown(inPage('input', 'checkbox'), { key: 'Escape' });
    fireEvent.keyDown(inPage('button'), { key: 'Escape' });
    expect(onEscape).toHaveBeenCalledTimes(3);
  });
});
