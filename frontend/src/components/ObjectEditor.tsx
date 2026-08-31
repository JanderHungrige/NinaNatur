import { useState } from 'react';

import { KINDS as KIND_LIST, PLANTING_KIND } from '../kinds';

/** What the editor is looking at. A bed and an obstacle differ in what they own. */
/**
 * What the editor is looking at.
 *
 * One shape, since Wave 11 made an element one thing. It used to be a union of
 * bed and obstacle, which is the schema's old split wearing a TypeScript
 * costume — and it made "say what this is" impossible to express, because a bed
 * could not become anything else.
 */
export interface EditableObject {
  id: number;
  /** What it is. Changing this is the whole point of the panel. */
  objectKind: string;
  /** The bed's own name; null on everything else. */
  name: string | null;
  label: string | null;
  /** None on a surface: an unrecorded height is not a zero. */
  height: number | null;
  heightAboveGround: number;
  /** How many plants stand in it, for the warning before they are lost. */
  plantings: number;
  /** 'polygon' | 'circle' | 'line'. A line is the only one with a width to set. */
  shape: string;
  width: number | null;
  /** A bed may differ from its garden: bought soil, a watered corner. */
  soilType: string | null;
  moisture: string | null;
}

interface Props {
  object: EditableObject;
  onSave: (changes: Record<string, string | number>) => void;
  onClose: () => void;
  busy: boolean;
}

/**
 * The vocabulary, with the numbers that make each kind a thing.
 *
 * One list, in ../kinds. This one used to be its own, and drifted: it offered
 * "Gebäude" for months after the server had replaced it with house and shed,
 * so choosing it wrote a kind nothing downstream understood.
 */
const KINDS = KIND_LIST.map((k) => ({ value: k.kind, label: k.label, height: k.height }));

export function ObjectEditor({ object, onSave, onClose, busy }: Props) {
  const [label, setLabel] = useState(object.label ?? '');
  const [objectKind, setObjectKind] = useState(object.objectKind);
  const [height, setHeight] = useState(object.height === null ? '' : String(object.height));
  const [raised, setRaised] = useState(String(object.heightAboveGround));
  const [width, setWidth] = useState(object.width === null ? '' : String(object.width));
  const [soil, setSoil] = useState(object.soilType ?? '');
  const [wet, setWet] = useState(object.moisture ?? '');
  /** Whether the height on screen is ours or theirs. */
  const [heightIsOurs, setHeightIsOurs] = useState(true);

  const named = KINDS.find((k) => k.value === objectKind)?.label ?? 'Objekt';
  const title = object.name ?? named;

  /** What a re-label away from a bed would cost. */
  const losing =
    object.objectKind === PLANTING_KIND && objectKind !== PLANTING_KIND
      ? object.plantings
      : 0;

  const changeKind = (value: string) => {
    setObjectKind(value);
    const suggested = KINDS.find((k) => k.value === value)?.height;
    // A default is a starting value, not a constraint: a user who typed 4 m for
    // their hedge has a 4 m hedge, whatever they call it afterwards.
    if (heightIsOurs && suggested != null) setHeight(String(suggested));
  };

  const save = () => {
    // The kind always goes: saying what a thing is *is* the panel, and Wave 11
    // made it a property rather than a table. A bed that keeps its kind simply
    // sends the same value back.
    const changes: Record<string, string | number> = { kind: objectKind, label };
    if (objectKind === PLANTING_KIND) {
      changes.height_above_ground = Number(raised);
      // Only when the user has actually said: an empty field means "whatever
      // the garden says", not "no soil".
      if (soil !== '') changes.soil_type = soil;
      if (wet !== '') changes.moisture = wet;
    } else if (height !== '') {
      changes.height = Number(height);
    }
    if (object.shape === 'line' && width !== '') changes.width = Number(width);
    onSave(changes);
  };

  return (
    <section className="panel object-editor" aria-labelledby="object-heading">
      <h2 id="object-heading">{title}</h2>

      {/* Always offered. A drawn shape has no kind until somebody says so, and
          a bed that turns out to be a pool has to be able to say it. */}
      <label htmlFor="object-kind">Art</label>
      <select
        id="object-kind"
        value={objectKind}
        disabled={busy}
        onChange={(e) => changeKind(e.target.value)}
      >
        {KINDS.map((k) => (
          <option key={k.value} value={k.value}>
            {k.label}
          </option>
        ))}
      </select>

      {losing > 0 && (
        <p className="hint object-editor__warning" role="alert">
          Hier stehen {losing === 1 ? 'eine Pflanze' : `${losing} Pflanzen`}. Beim
          Speichern als „{named}" {losing === 1 ? 'geht sie' : 'gehen sie'} verloren.
        </p>
      )}

      {object.shape === 'line' && (
        <>
          <label htmlFor="object-width">Breite (m)</label>
          <input
            id="object-width"
            type="number"
            min="0.05"
            step="any"
            value={width}
            disabled={busy}
            onChange={(e) => setWidth(e.target.value)}
          />
          <p className="hint">
            Ein Weg ist eine Linie mit einer Breite — zwei Zahlen pro Ecke statt
            zwanzig Punkten um einen Streifen herum.
          </p>
        </>
      )}

      {objectKind !== PLANTING_KIND && (
        <>
          <label htmlFor="object-height">Höhe (m)</label>
          <input
            id="object-height"
            type="number"
            min="0"
            step="0.1"
            value={height}
            disabled={busy}
            onChange={(e) => {
              setHeight(e.target.value);
              setHeightIsOurs(false);
            }}
          />
        </>
      )}

      {objectKind === PLANTING_KIND && (
        <>
          <label htmlFor="object-raised">Höhe über Grund (m)</label>
          <input
            id="object-raised"
            type="number"
            min="0"
            step="0.1"
            value={raised}
            disabled={busy}
            onChange={(e) => setRaised(e.target.value)}
          />
          <p className="hint">
            Ein Hochbeet steht über niedrigen Zäunen und bekommt dadurch mehr
            Sonne. Die Lichtwerte werden nach dem Speichern neu berechnet.
          </p>

          <label htmlFor="object-soil">Boden</label>
          <select id="object-soil" value={soil} disabled={busy}
                  onChange={(e) => setSoil(e.target.value)}>
            <option value="">wie im Garten</option>
            <option value="sand">sandig</option>
            <option value="loam">lehmig</option>
            <option value="clay">tonig</option>
            <option value="humus">humos</option>
          </select>

          <label htmlFor="object-moisture">Feuchte</label>
          <select id="object-moisture" value={wet} disabled={busy}
                  onChange={(e) => setWet(e.target.value)}>
            <option value="">wie im Garten</option>
            <option value="dry">trocken</option>
            <option value="fresh">frisch</option>
            <option value="moist">feucht</option>
            <option value="wet">nass</option>
          </select>
        </>
      )}

      <label htmlFor="object-label">Bezeichnung</label>
      <input
        id="object-label"
        type="text"
        value={label}
        disabled={busy}
        placeholder="z. B. Die Buche vom Nachbarn"
        onChange={(e) => setLabel(e.target.value)}
      />
      <p className="hint">Nur für dich — die Bezeichnung wird nicht ausgewertet.</p>

      <div className="object-editor__actions">
        <button type="button" onClick={save} disabled={busy}>
          Speichern
        </button>
        <button type="button" className="link-button" onClick={onClose}>
          Abbrechen
        </button>
      </div>
    </section>
  );
}
