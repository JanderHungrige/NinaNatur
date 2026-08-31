import { useEffect, useRef, useState } from 'react';

import { KINDS, PLANTING_KIND, labelOf } from '../kinds';

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
  /** 'polygon' | 'circle' | 'line'. Only a line has a width to set. */
  shape: string;
  height: number | null;
  width: number | null;
  soilType: string | null;
  moisture: string | null;
  heightAboveGround: number;
  onSave: (changes: Record<string, string | number>) => void;
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
  shape,
  height,
  width,
  soilType,
  moisture,
  heightAboveGround,
  onSave,
  onDelete,
  onClose,
  busy,
}: Props) {
  const [chosen, setChosen] = useState(kind);
  const [text, setText] = useState(label ?? '');
  // Everything the editor panel used to hold. It was a block in the sidebar
  // showing whatever happened to be selected, and it is gone: this menu is
  // already at the element, and two places to edit one thing is one too many.
  const [tall, setTall] = useState(height === null ? '' : String(height));
  const [band, setBand] = useState(width === null ? '' : String(width));
  const [soil, setSoil] = useState(soilType ?? '');
  const [wet, setWet] = useState(moisture ?? '');
  const [raised, setRaised] = useState(String(heightAboveGround));
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

      {chosen !== PLANTING_KIND && (
        <>
          <label htmlFor="menu-height">Höhe (m)</label>
          <input id="menu-height" type="number" min="0" step="0.1" value={tall}
                 disabled={busy} onChange={(e) => setTall(e.target.value)} />
        </>
      )}

      {shape === 'line' && (
        <>
          <label htmlFor="menu-width">Breite (m)</label>
          <input id="menu-width" type="number" min="0.05" step="any" value={band}
                 disabled={busy} onChange={(e) => setBand(e.target.value)} />
        </>
      )}

      {chosen === PLANTING_KIND && (
        <>
          <label htmlFor="menu-raised">Höhe über Grund (m)</label>
          <input id="menu-raised" type="number" min="0" step="0.1" value={raised}
                 disabled={busy} onChange={(e) => setRaised(e.target.value)} />

          <label htmlFor="menu-soil">Boden</label>
          <select id="menu-soil" value={soil} disabled={busy}
                  onChange={(e) => setSoil(e.target.value)}>
            <option value="">wie im Garten</option>
            <option value="sand">sandig</option>
            <option value="loam">lehmig</option>
            <option value="clay">tonig</option>
            <option value="humus">humos</option>
          </select>

          <label htmlFor="menu-moisture">Feuchte</label>
          <select id="menu-moisture" value={wet} disabled={busy}
                  onChange={(e) => setWet(e.target.value)}>
            <option value="">wie im Garten</option>
            <option value="dry">trocken</option>
            <option value="fresh">frisch</option>
            <option value="moist">feucht</option>
            <option value="wet">nass</option>
          </select>
        </>
      )}

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
              onClick={() => {
                const changes: Record<string, string | number> = {
                  kind: chosen,
                  label: text,
                };
                if (chosen === PLANTING_KIND) {
                  changes.height_above_ground = Number(raised);
                  // Empty means "whatever the garden says", not "no soil".
                  if (soil !== '') changes.soil_type = soil;
                  if (wet !== '') changes.moisture = wet;
                } else if (tall !== '') {
                  changes.height = Number(tall);
                }
                if (shape === 'line' && band !== '') changes.width = Number(band);
                onSave(changes);
              }}
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
