import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { Tool } from '../canvas/shapes';
import { ToolRail, hintFor } from './ToolRail';

function rail(
  active: Tool | null = null,
  busy = false,
  orientation: 'vertical' | 'horizontal' = 'vertical',
) {
  const onPick = vi.fn();
  render(<ToolRail active={active} onPick={onPick} busy={busy} orientation={orientation} />);
  return { onPick, toolbar: screen.getByRole('toolbar', { name: 'Werkzeuge' }) };
}

const tools = (): HTMLElement[] => screen.getAllByRole('button');

describe('ToolRail', () => {
  it('is a toolbar that says which way it runs', () => {
    expect(rail(null, false, 'vertical').toolbar.getAttribute('aria-orientation')).toBe('vertical');
  });

  it('names every tool by the words it shows, in the order they stand', () => {
    rail();
    expect(tools().map((b) => b.textContent?.trim())).toEqual([
      'Auswählen', 'Rechteck', 'Kreis', 'Dreieck', 'Vieleck', 'Freihand',
    ]);
  });

  it('names every tool with a label the browser keeps, and keeps the tooltip out of it', () => {
    // Measured on the preview (V0.20.155): Chrome's accessibility tree gave these
    // six buttons no name at all from the visually hidden text alone, though
    // jsdom computed one. The label carries the same words the tooltip shows.
    rail();
    expect(tools().map((b) => b.getAttribute('aria-label'))).toEqual([
      'Auswählen', 'Rechteck', 'Kreis', 'Dreieck', 'Vieleck', 'Freihand',
    ]);
    for (const tool of tools()) {
      expect(tool.querySelector('.tool-rail__label')?.getAttribute('aria-hidden')).toBe('true');
    }
  });

  it('is one stop in the tab order: the armed tool, or Auswählen when none is', () => {
    rail('circle');
    expect(tools().filter((b) => b.tabIndex === 0).map((b) => b.textContent?.trim())).toEqual([
      'Kreis',
    ]);
  });

  it('moves along the rail with the arrow keys, and to its ends with Home and End', () => {
    rail();
    const [select, rect, circle, , , freehand] = tools();
    select!.focus();
    fireEvent.keyDown(select!, { key: 'ArrowDown' });
    expect(document.activeElement).toBe(rect);
    // The stop moves with the focus, so Tab out and back returns to it.
    expect(rect!.tabIndex).toBe(0);
    expect(select!.tabIndex).toBe(-1);
    fireEvent.keyDown(rect!, { key: 'ArrowRight' });
    expect(document.activeElement).toBe(circle);
    fireEvent.keyDown(circle!, { key: 'ArrowUp' });
    expect(document.activeElement).toBe(rect);
    fireEvent.keyDown(rect!, { key: 'End' });
    expect(document.activeElement).toBe(freehand);
    fireEvent.keyDown(freehand!, { key: 'Home' });
    expect(document.activeElement).toBe(select);
  });

  it('arms the tool that is pressed', () => {
    const { onPick } = rail();
    fireEvent.click(screen.getByRole('button', { name: 'Rechteck' }));
    expect(onPick).toHaveBeenCalledWith('rect');
  });

  it('shows the armed tool as pressed, and puts it down from Auswählen or from itself', () => {
    const { onPick } = rail('polygon');
    expect(screen.getByRole('button', { name: 'Vieleck' }).getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByRole('button', { name: 'Kreis' }).getAttribute('aria-pressed')).toBe('false');
    fireEvent.click(screen.getByRole('button', { name: 'Vieleck' }));
    fireEvent.click(screen.getByRole('button', { name: 'Auswählen' }));
    expect(onPick.mock.calls).toEqual([[null], [null]]);
  });

  it('keeps its tools focusable while busy, and ignores them', () => {
    // A disabled button cannot hold focus: it would throw the keyboard out of
    // the toolbar every time a request was running.
    const { onPick } = rail(null, true);
    const rect = screen.getByRole('button', { name: 'Rechteck' }) as HTMLButtonElement;
    expect(rect.getAttribute('aria-disabled')).toBe('true');
    expect(rect.disabled).toBe(false);
    fireEvent.click(rect);
    expect(onPick).not.toHaveBeenCalled();
  });

  it('says what the armed tool expects, and what to do when none is armed', () => {
    expect(hintFor('polygon')).toMatch(/Ecke für Ecke/);
    expect(hintFor('freehand')).toMatch(/In einem Zug/);
    expect(hintFor(null)).toMatch(/Wähle eine Form/);
  });
});
