import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { Snap } from '../workspace/sheet';
import { SheetHandle } from './SheetHandle';

/** The handle over 400 px of space, on a clock the test moves by hand. */
function handle(snap: Snap = 'peek') {
  let clock = 0;
  const onSnap = vi.fn();
  const onDrag = vi.fn();
  render(
    <SheetHandle snap={snap} onSnap={onSnap} onDrag={onDrag} controls="details" space={() => 400} now={() => clock} />,
  );
  return {
    onSnap,
    onDrag,
    element: screen.getByRole('separator', { name: 'Höhe der Details' }),
    tick: (ms: number) => {
      clock += ms;
    },
  };
}

const press = (element: HTMLElement, key: string) => fireEvent.keyDown(element, { key });

describe('SheetHandle', () => {
  it('is a window splitter that says how high the details stand, and which details', () => {
    const { element } = handle();
    expect(element.tabIndex).toBe(0);
    expect(element.getAttribute('aria-orientation')).toBe('horizontal');
    expect(element.getAttribute('aria-controls')).toBe('details');
    expect(element.getAttribute('aria-valuemin')).toBe('25');
    expect(element.getAttribute('aria-valuemax')).toBe('90');
    expect(element.getAttribute('aria-valuenow')).toBe('25');
    expect(element.getAttribute('aria-valuetext')).toBe('ein Viertel');
  });

  it('says each height it stands at', () => {
    const { element } = handle('half');
    expect(element.getAttribute('aria-valuenow')).toBe('60');
    expect(element.getAttribute('aria-valuetext')).toBe('gut die Hälfte');
  });

  it('moves one height with the arrows and the Page keys', () => {
    const { element, onSnap } = handle();
    press(element, 'ArrowUp');
    press(element, 'PageUp');
    press(element, 'ArrowDown');
    expect(onSnap.mock.calls).toEqual([['half'], ['half'], ['peek']]);
  });

  it('lowers from 60 % with Arrow Down and Page Down', () => {
    const { element, onSnap } = handle('half');
    press(element, 'ArrowDown');
    press(element, 'PageDown');
    expect(onSnap.mock.calls).toEqual([['peek'], ['peek']]);
  });

  it('goes to the ends with Home and End', () => {
    const { element, onSnap } = handle('half');
    press(element, 'End');
    press(element, 'Home');
    expect(onSnap.mock.calls).toEqual([['full'], ['peek']]);
  });

  it('toggles a quarter and 60 % with Enter', () => {
    const { element, onSnap } = handle();
    press(element, 'Enter');
    expect(onSnap).toHaveBeenLastCalledWith('half');
  });

  it('comes down from 90 % to 60 % with Enter', () => {
    const { element, onSnap } = handle('full');
    press(element, 'Enter');
    expect(onSnap).toHaveBeenLastCalledWith('half');
  });

  it('leaves keys it has no use for to the page', () => {
    const { element, onSnap } = handle();
    press(element, 'Tab');
    press(element, 'Escape');
    expect(onSnap).not.toHaveBeenCalled();
  });

  it('follows a slow drag and comes to rest at the nearest height', () => {
    const { element, onSnap, onDrag, tick } = handle();
    fireEvent.pointerDown(element, { clientY: 600, pointerId: 1 });
    tick(300);
    fireEvent.pointerMove(element, { clientY: 460, pointerId: 1 });
    tick(300);
    fireEvent.pointerMove(element, { clientY: 440, pointerId: 1 });
    tick(300);
    fireEvent.pointerUp(element, { clientY: 440, pointerId: 1 });
    expect(onDrag.mock.calls.map(([fraction]) => (fraction === null ? null : Number(fraction.toFixed(2))))).toEqual([
      0.6,
      0.65,
      null,
    ]);
    expect(onSnap).toHaveBeenCalledWith('half');
  });

  it('goes on to the next height the way it was flicked', () => {
    const { element, onSnap, tick } = handle();
    fireEvent.pointerDown(element, { clientY: 600, pointerId: 1 });
    tick(40);
    fireEvent.pointerMove(element, { clientY: 500, pointerId: 1 });
    tick(40);
    fireEvent.pointerUp(element, { clientY: 440, pointerId: 1 });
    // Nearest to 0.65 is 60 %; the flick carries it on to 90 %.
    expect(onSnap).toHaveBeenCalledWith('full');
  });

  it('takes a touch that does not travel for Enter', () => {
    const { element, onSnap, onDrag, tick } = handle();
    fireEvent.pointerDown(element, { clientY: 600, pointerId: 1 });
    tick(100);
    fireEvent.pointerUp(element, { clientY: 602, pointerId: 1 });
    expect(onSnap).toHaveBeenCalledWith('half');
    expect(onDrag.mock.calls.every(([fraction]) => fraction === null)).toBe(true);
  });

  it('lets a cancelled drag go without moving the sheet', () => {
    const { element, onSnap, onDrag } = handle();
    fireEvent.pointerDown(element, { clientY: 600, pointerId: 1 });
    fireEvent.pointerMove(element, { clientY: 500, pointerId: 1 });
    fireEvent.pointerCancel(element, { pointerId: 1 });
    expect(onDrag).toHaveBeenLastCalledWith(null);
    expect(onSnap).not.toHaveBeenCalled();
  });
});
