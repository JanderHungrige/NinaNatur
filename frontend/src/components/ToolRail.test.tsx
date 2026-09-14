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

const NAMES = ['Auswählen', 'Rechteck', 'Kreis', 'Dreieck', 'Vieleck', 'Freihand', 'Standpunkt'];

describe('ToolRail', () => {
  it('is a toolbar that says which way it runs', () => {
    expect(rail(null, false, 'vertical').toolbar.getAttribute('aria-orientation')).toBe('vertical');
  });

  it('names every tool by the words it shows, in the order they stand', () => {
    // Doc 89 added Standpunkt, last: placing a viewpoint is a way of using the
    // plan, as drawing on it is.
    rail();
    expect(tools().map((b) => b.textContent?.trim())).toEqual(NAMES);
  });

  it('names every tool by aria-label too, and keeps the tooltip out of the name', () => {
    // A tree that leaves clipped text out — the Browser pane's, on V0.20.155 —
    // listed these six buttons without a name. Chrome's own tree named them from
    // the hidden text; the label makes every tree agree, in the tooltip's words.
    rail();
    expect(tools().map((b) => b.getAttribute('aria-label'))).toEqual(NAMES);
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
    const [select, rect, circle, , , , standpoint] = tools();
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
    expect(document.activeElement).toBe(standpoint);
    fireEvent.keyDown(standpoint!, { key: 'Home' });
    expect(document.activeElement).toBe(select);
  });

  it('arms the tool that is pressed', () => {
    const { onPick } = rail();
    fireEvent.click(screen.getByRole('button', { name: 'Rechteck' }));
    fireEvent.click(screen.getByRole('button', { name: 'Standpunkt' }));
    expect(onPick.mock.calls).toEqual([['rect'], ['viewpoint']]);
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
    expect(hintFor('viewpoint')).toMatch(/wo du stehst/);
    expect(hintFor(null)).toMatch(/Wähle eine Form/);
  });
});
