import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { useShortcutHelp } from './useShortcutHelp';

const press = (init: KeyboardEventInit, target: EventTarget = window) =>
  act(() => {
    target.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, ...init }));
  });

function button(parent: HTMLElement = document.body): HTMLButtonElement {
  const element = document.createElement('button');
  parent.append(element);
  return element;
}

afterEach(() => {
  document.body.innerHTML = '';
});

describe('useShortcutHelp', () => {
  it('opens on ?', () => {
    const { result } = renderHook(() => useShortcutHelp());
    expect(result.current.open).toBe(false);
    press({ key: '?' });
    expect(result.current.open).toBe(true);
  });

  it('leaves a ? typed into a field to the field', () => {
    const { result } = renderHook(() => useShortcutHelp());
    const field = document.createElement('input');
    document.body.append(field);
    press({ key: '?' }, field);
    expect(result.current.open).toBe(false);
  });

  it('leaves ? held with Ctrl, Cmd or Alt to the browser', () => {
    const { result } = renderHook(() => useShortcutHelp());
    press({ key: '?', ctrlKey: true });
    press({ key: '?', metaKey: true });
    press({ key: '?', altKey: true });
    expect(result.current.open).toBe(false);
  });

  it('gives the focus back to where it was when the help closes', () => {
    const opener = button();
    opener.focus();
    const { result } = renderHook(() => useShortcutHelp());
    act(() => result.current.show());
    button().focus(); // the help's own button
    act(() => result.current.hide());
    expect(result.current.open).toBe(false);
    expect(document.activeElement).toBe(opener);
  });

  it('gives it to the menu’s toggle when the menu has folded the opener away', () => {
    // On a narrow window Tastenkürzel is behind Menü, and choosing it closes the
    // menu: the button it was opened from can no longer take the focus.
    const toggle = button();
    toggle.setAttribute('aria-controls', 'more');
    const menu = document.createElement('div');
    menu.id = 'more';
    document.body.append(menu);
    const opener = button(menu);
    opener.focus();
    const { result } = renderHook(() => useShortcutHelp());
    act(() => result.current.show());
    button().focus();
    opener.disabled = true; // as unfocusable as a button in a folded menu
    act(() => result.current.hide());
    expect(document.activeElement).toBe(toggle);
  });
});
