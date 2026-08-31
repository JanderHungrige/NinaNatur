import { useEffect, useRef, useState } from 'react';

import { KINDS, labelOf } from '../kinds';

interface Props {
  /** Where the menu opens, in page pixels. */
  at: { x: number; y: number };
  kind: string;
  label: string | null;
  /** What it covers, so a menu opened on the wrong one of two overlapping
   *  shapes says so before anything is changed. */
  area: number;
  onSave: (changes: { kind: string; label: string }) => void;
  onClose: () => void;
  busy: boolean;
}

/**
 * Saying what a thing is, at the thing.
 *
 * The editor panel already does this, and it is across the page from the plan.
 * This is the short way — not the only way, which is why the panel stays: a
 * menu that only a right-click reaches leaves out everyone working from the
 * keyboard.
 */
export function ElementMenu({ at, kind, label, area, onSave, onClose, busy }: Props) {
  const [chosen, setChosen] = useState(kind);
  const [text, setText] = useState(label ?? '');
  const box = useRef<HTMLDivElement | null>(null);

  // Focus goes into the menu when it opens, and Escape closes it. Without both
  // it is a trap for anyone not using a pointer.
  useEffect(() => {
    box.current?.querySelector('select')?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      ref={box}
      className="element-menu"
      role="dialog"
      aria-label="Was ist das?"
      style={{ left: at.x, top: at.y }}
    >
      {/* Which element this is about. Two shapes on top of each other take the
          same right-click, and without this the user names one and watches the
          other not change. */}
      <p className="element-menu__subject">
        {labelOf(kind)}
        {label !== null && label !== '' ? ` — ${label}` : ''}
        {`, ${area.toFixed(1).replace('.', ',')} m²`}
      </p>
      <label htmlFor="menu-kind">Art</label>
      <select
        id="menu-kind"
        value={chosen}
        disabled={busy}
        onChange={(e) => setChosen(e.target.value)}
      >
        {KINDS.map((k) => (
          <option key={k.kind} value={k.kind}>{k.label}</option>
        ))}
      </select>

      <label htmlFor="menu-label">Bezeichnung</label>
      <input
        id="menu-label"
        type="text"
        value={text}
        disabled={busy}
        placeholder="z. B. Die Buche vom Nachbarn"
        onChange={(e) => setText(e.target.value)}
      />

      <div className="element-menu__actions">
        <button
          type="button"
          disabled={busy}
          onClick={() => onSave({ kind: chosen, label: text })}
        >
          Übernehmen
        </button>
        <button type="button" className="link-button" onClick={onClose}>
          Abbrechen
        </button>
      </div>
    </div>
  );
}
