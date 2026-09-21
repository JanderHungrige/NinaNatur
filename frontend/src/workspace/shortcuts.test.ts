import { describe, expect, it } from 'vitest';

import { SHORTCUTS } from './shortcuts';

/* Doc 92: the help lists what the code answers, and nothing it does not. */

const chords = (heading: string) =>
  SHORTCUTS.find((group) => group.heading === heading)?.shortcuts.flatMap((s) => s.keys.map((c) => c.join('+'))) ?? [];

describe('SHORTCUTS', () => {
  it('is grouped by where the keys apply, the whole workspace first', () => {
    expect(SHORTCUTS.map((group) => group.heading)).toEqual([
      'Überall',
      'Im Plan',
      'In der Werkzeugleiste',
      'In den Vorschlägen',
      'Auf einem schmalen Fenster',
    ]);
  });

  it('names what the whole workspace answers: this help, Escape and undo', () => {
    // useShortcutHelp, useEscapeKey, useUndoShortcut.
    expect(chords('Überall')).toEqual(['?', 'Esc', 'Strg+Z']);
  });

  it('names what the plan answers', () => {
    // CanvasScene and ClusterLayer (Tab, Enter, Space, Shift+F10, the context
    // menu key), useClipboard (C and V), useViewport (the wheel), and
    // useCanvasGestures and useHandleDrag (Alt).
    expect(chords('Im Plan')).toEqual([
      'Tab', 'Eingabe', 'Leertaste', 'Umschalt+F10', 'Kontextmenü', 'Strg+C', 'Strg+V', 'Mausrad', 'Alt',
    ]);
  });

  it('names the keys of the tools, the suggestions and the sheet', () => {
    // ToolRail: all four arrows. SuggestionWindow: STEPS. SheetHandle: KEYS,
    // and the Inspector's Escape at 90 %.
    expect(chords('In der Werkzeugleiste')).toEqual(['Pfeiltasten', 'Pos1', 'Ende']);
    expect(chords('In den Vorschlägen')).toEqual(['↑', '↓', 'Bild↑', 'Bild↓', 'Pos1', 'Ende']);
    expect(chords('Auf einem schmalen Fenster')).toEqual(['↑', '↓', 'Pos1', 'Ende', 'Eingabe', 'Esc']);
  });

  it('says in words what every key does', () => {
    for (const group of SHORTCUTS) {
      for (const shortcut of group.shortcuts) {
        expect(shortcut.keys.length).toBeGreaterThan(0);
        expect(shortcut.does.length).toBeGreaterThan(8);
      }
    }
  });
});
