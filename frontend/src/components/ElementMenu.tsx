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
  /** How many plants stand in it, for the warning before they go with it. */
  plantings: number;
  onSave: (changes: { kind: string; label: string }) => void;
  onDelete: () => void;
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
export function ElementMenu({
  at,
  kind,
  label,
  area,
  plantings,
  onSave,
  onDelete,
  onClose,
  busy,
}: Props) {
  const [chosen, setChosen] = useState(kind);
  const [text, setText] = useState(label ?? '');
  const box = useRef<HTMLDivElement | null>(null);
  /** Deleting asks first. An element cannot be got back, and this menu is one
   *  right-click away from every shape on the plan. */
  const [confirming, setConfirming] = useState(false);

  // Focus goes into the menu when it opens, and Escape closes it. Without both
  // it is a trap for anyone not using a pointer.
  //
  // A pointer landing anywhere else closes it too: clicking another shape used
  // to leave the menu hanging over the plan, still asking about the shape
  // before — which is how somebody ends up naming the wrong thing. The listener
  // is added after mount, so the right-click that opened the menu cannot close
  // it again — and it listens in the capture phase, because grabbing a shape
  // stops the event propagating so the plan does not read it as a pan. A
  // bubbling listener would never hear the one click that matters most.
  useEffect(() => {
    box.current?.querySelector('select')?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    const onPointer = (event: PointerEvent) => {
      const target = event.target;
      if (target instanceof Node && box.current?.contains(target) === true) return;
      onClose();
    };
    window.addEventListener('keydown', onKey);
    window.addEventListener('pointerdown', onPointer, true);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('pointerdown', onPointer, true);
    };
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

      {confirming && plantings > 0 && (
        <p className="hint element-menu__warning" role="alert">
          Hier {plantings === 1 ? 'steht eine Pflanze' : `stehen ${plantings} Pflanzen`}.
          {plantings === 1 ? ' Sie geht' : ' Sie gehen'} mit verloren.
        </p>
      )}

      <div className="element-menu__actions">
        {confirming ? (
          <>
            <button
              type="button"
              className="element-menu__danger"
              disabled={busy}
              onClick={onDelete}
            >
              Endgültig löschen
            </button>
            <button
              type="button"
              className="link-button"
              disabled={busy}
              onClick={() => setConfirming(false)}
            >
              Doch nicht
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              disabled={busy}
              onClick={() => onSave({ kind: chosen, label: text })}
            >
              Übernehmen
            </button>
            <button
              type="button"
              className="link-button element-menu__delete"
              disabled={busy}
              onClick={() => setConfirming(true)}
            >
              Löschen
            </button>
            <button type="button" className="link-button" onClick={onClose}>
              Abbrechen
            </button>
          </>
        )}
      </div>
    </div>
  );
}
