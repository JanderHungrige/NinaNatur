import { type KeyboardEvent, useRef, useState } from 'react';

import type { Tool } from '../canvas/shapes';

interface Props {
  active: Tool | null;
  onPick: (tool: Tool | null) => void;
  /** A request is running: the tools stay focusable and ignore presses. */
  busy: boolean;
  /** Up the side of the plan, or across above it where the window is narrow. */
  orientation: 'vertical' | 'horizontal';
}

interface RailTool {
  tool: Tool | null;
  label: string;
  hint: string;
  /** One path in a 24-unit box, drawn as a line. */
  icon: string;
}

export const RAIL_TOOLS: readonly RailTool[] = [
  {
    tool: null,
    label: 'Auswählen',
    hint: 'Wähle eine Form und zieh sie im Plan auf. Danach klickst du sie an und sagst, was sie ist.',
    icon: 'M6 3l12 8.5-5.2 1.3 3 6.4-2.4 1.1-3-6.4L6 17.5z',
  },
  { tool: 'rect', label: 'Rechteck', hint: 'Aufziehen. Ecken bleiben rechtwinklig.', icon: 'M4 6h16v12H4z' },
  {
    tool: 'circle',
    label: 'Kreis',
    hint: 'Aufziehen — die kleinere Seite ist der Durchmesser.',
    icon: 'M12 4a8 8 0 1 0 0.01 0z',
  },
  { tool: 'triangle', label: 'Dreieck', hint: 'Aufziehen.', icon: 'M12 4l9 16H3z' },
  { tool: 'polygon', label: 'Vieleck', hint: 'Ecke für Ecke klicken, dann „Fertig".', icon: 'M12 3l8 6-3 11H7L4 9z' },
  {
    tool: 'freehand',
    label: 'Freihand',
    hint: 'In einem Zug ziehen — der Plan glättet die Linie.',
    icon: 'M3 17c3-7 5-7 7-2.5s4 4 6-2.5 3.5-5 5-2.5',
  },
];

/** What the armed tool expects of the next gesture, or how to start when none is armed. */
export function hintFor(active: Tool | null): string {
  return (RAIL_TOOLS.find((t) => t.tool === active) ?? RAIL_TOOLS[0]!).hint;
}

/** Where the arrow keys lead from `index`, or null for a key the rail does not use. */
function stepFrom(key: string, index: number): number | null {
  const last = RAIL_TOOLS.length - 1;
  if (key === 'ArrowDown' || key === 'ArrowRight') return index === last ? 0 : index + 1;
  if (key === 'ArrowUp' || key === 'ArrowLeft') return index === 0 ? last : index - 1;
  if (key === 'Home') return 0;
  if (key === 'End') return last;
  return null;
}

/**
 * What you draw with, down the side of the plan (doc 87).
 *
 * A toolbar is one stop in the tab order: arrow keys move between its tools and
 * Enter or Space presses one, which is what a keyboard and a screen reader
 * already expect of it. Both arrow pairs work, because the rail runs across the
 * page where the window is narrow.
 *
 * Busy does not disable the tools. A disabled button cannot hold focus, so every
 * running request would throw the keyboard out of the toolbar; they are marked
 * `aria-disabled` and ignore presses instead.
 *
 * Each tool is also named by `aria-label`, in the words its tooltip shows on
 * hover and focus. Chrome's own tree names the buttons from the hidden text as
 * well (read over CDP); the label is for trees that leave clipped text out, as
 * the Browser pane's does, so that every reader gets the same name.
 */
export function ToolRail({ active, onPick, busy, orientation }: Props) {
  const armed = Math.max(0, RAIL_TOOLS.findIndex((t) => t.tool === active));
  // The one tab stop follows the focus, and starts on the armed tool.
  const [stop, setStop] = useState<number | null>(null);
  const buttons = useRef<Array<HTMLButtonElement | null>>([]);
  const current = stop ?? armed;

  const move = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const next = stepFrom(event.key, index);
    if (next === null) return;
    event.preventDefault();
    setStop(next);
    buttons.current[next]?.focus();
  };

  const press = (tool: Tool | null) => {
    if (busy) return;
    // The same press that arms a tool is the one reached for to put it down.
    onPick(tool !== null && tool === active ? null : tool);
  };

  return (
    <div className="tool-rail" role="toolbar" aria-label="Werkzeuge" aria-orientation={orientation}>
      {RAIL_TOOLS.map(({ tool, label, icon }, index) => (
        <button
          key={label}
          ref={(element) => {
            buttons.current[index] = element;
          }}
          type="button"
          className="tool-rail__tool"
          aria-label={label}
          aria-pressed={tool === active}
          aria-disabled={busy || undefined}
          tabIndex={index === current ? 0 : -1}
          onFocus={() => setStop(index)}
          onKeyDown={(event) => move(event, index)}
          onClick={() => press(tool)}
        >
          <svg className="tool-rail__icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d={icon} />
          </svg>
          <span className="tool-rail__label" aria-hidden="true">
            {label}
          </span>
        </button>
      ))}
    </div>
  );
}
