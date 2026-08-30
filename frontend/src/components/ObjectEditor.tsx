import { useState } from 'react';

import { KINDS as KIND_LIST } from '../kinds';

/** What the editor is looking at. A bed and an obstacle differ in what they own. */
export type EditableObject =
  | {
      kind: 'bed';
      id: number;
      name: string;
      label: string | null;
      heightAboveGround: number;
    }
  | {
      kind: 'obstacle';
      id: number;
      objectKind: string;
      label: string | null;
      /** None on a surface: an unrecorded height is not a zero. */
      height: number | null;
      width: number;
      depth: number | null;
    };

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
  const [objectKind, setObjectKind] = useState(
    object.kind === 'obstacle' ? object.objectKind : '',
  );
  const [height, setHeight] = useState(
    object.kind === 'obstacle' && object.height !== null ? String(object.height) : '',
  );
  const [raised, setRaised] = useState(
    object.kind === 'bed' ? String(object.heightAboveGround) : '',
  );
  /** Whether the height on screen is ours or theirs. */
  const [heightIsOurs, setHeightIsOurs] = useState(true);

  const title = object.kind === 'bed' ? object.name : (
    KINDS.find((k) => k.value === objectKind)?.label ?? 'Objekt'
  );

  const changeKind = (value: string) => {
    setObjectKind(value);
    const suggested = KINDS.find((k) => k.value === value)?.height;
    // A default is a starting value, not a constraint: a user who typed 4 m for
    // their hedge has a 4 m hedge, whatever they call it afterwards.
    if (heightIsOurs && suggested != null) setHeight(String(suggested));
  };

  const save = () => {
    if (object.kind === 'bed') {
      onSave({ height_above_ground: Number(raised), label });
    } else {
      onSave({ kind: objectKind, height: Number(height), label });
    }
  };

  return (
    <section className="panel object-editor" aria-labelledby="object-heading">
      <h2 id="object-heading">{title}</h2>

      {object.kind === 'obstacle' && (
        <>
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

      {object.kind === 'bed' && (
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
