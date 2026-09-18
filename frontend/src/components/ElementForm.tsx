import { useEffect, useId, useRef, useState } from 'react';

import type { FormValues } from '../garden/selection';
import { eavesNote, roofNote } from '../heights';
import { KINDS, PLANTING_KIND } from '../kinds';
import { ROOFED, ROOFS } from '../roofs';

interface Props extends FormValues {
  /** What the section asks. */
  heading: string;
  /** Null is a value, not an omission: it is how a typed-in eaves height is put
   *  back to "nobody has said". */
  onSave: (changes: Record<string, string | number | null>) => void;
  onDelete: () => void;
  /** Leaving without saving: back to the garden, or a bed's form folded away. */
  onCancel: () => void;
  busy: boolean;
  /** Asked about from the plan: the first field takes the focus. */
  takeFocus: boolean;
  onFocusTaken?: (() => void) | undefined;
}

/**
 * Saying what a thing is, in the details beside it (docs 51, 88).
 *
 * It was a popover at the shape, anchored to it and closed by a click anywhere
 * else. In the workspace the details already stand beside the plan, so the form
 * lives there: one place to describe an element, and the selection decides which
 * element that is.
 *
 * Nothing in it is ever disabled while a request runs. A disabled control cannot
 * hold the focus, so every request would throw the keyboard out of the form; the
 * buttons are `aria-disabled` and ignore presses instead, the rule the tool rail
 * follows (doc 87).
 */
export function ElementForm({
  heading,
  kind,
  label,
  plantings,
  shape,
  roof,
  roofSource,
  eavesM,
  eavesSource,
  height,
  width,
  soilType,
  moisture,
  heightAboveGround,
  onSave,
  onDelete,
  onCancel,
  busy,
  takeFocus,
  onFocusTaken,
}: Props) {
  const id = useId();
  const field = (name: string) => `${id}-${name}`;
  const box = useRef<HTMLElement | null>(null);
  const [chosen, setChosen] = useState(kind);
  const [text, setText] = useState(label ?? '');
  // What the fields opened with, so that only what changed is sent (doc 93).
  const tallAtStart = height === null ? '' : String(height);
  const eavesAtStart = eavesM === null ? '' : String(eavesM);
  const [tall, setTall] = useState(tallAtStart);
  const [roofShape, setRoofShape] = useState(roof);
  const [eaves, setEaves] = useState(eavesAtStart);
  const [band, setBand] = useState(width === null ? '' : String(width));
  const [soil, setSoil] = useState(soilType ?? '');
  const [wet, setWet] = useState(moisture ?? '');
  const [raised, setRaised] = useState(String(heightAboveGround));
  /** Deleting asks first. An element cannot be got back. */
  const [confirming, setConfirming] = useState(false);

  // Asked about from the plan — right-click, Shift+F10, the context-menu key —
  // the question lands in the first field. Only then: choosing a shape on the
  // plan must not pull the keyboard off the plan.
  useEffect(() => {
    if (!takeFocus) return;
    box.current?.querySelector('select')?.focus();
    onFocusTaken?.();
  }, [takeFocus, onFocusTaken]);

  /** A press while a request runs does nothing; see above for why it is not disabled. */
  const unlessBusy = (action: () => void) => () => {
    if (!busy) action();
  };

  const save = () => {
    const changes: Record<string, string | number | null> = { kind: chosen, label: text };
    if (chosen === PLANTING_KIND) {
      changes.height_above_ground = Number(raised);
      // Empty means "whatever the garden says", not "no soil".
      if (soil !== '') changes.soil_type = soil;
      if (wet !== '') changes.moisture = wet;
    } else if (tall !== '' && tall !== tallAtStart) {
      changes.height = Number(tall);
    }
    // Only what was changed (doc 93). The server takes a value in the body as
    // the gardener's word on it, and a rename is nobody's word on the roof.
    if (ROOFED.has(chosen) && roofShape !== roof) changes.roof = roofShape;
    if (ROOFED.has(chosen) && eaves !== eavesAtStart) {
      // Empty is "nobody has said", which is a value: it puts the building back
      // on the assumed eaves rather than on zero.
      changes.eaves_m = eaves === '' ? null : Number(eaves);
    }
    if (shape === 'line' && band !== '') changes.width = Number(band);
    onSave(changes);
  };

  // Where the stored values came from. A note belongs to the value it describes:
  // once the field is changed, the value is the gardener's and says nothing.
  const ridge = tall === '' || !Number.isFinite(Number(tall)) ? null : Number(tall);
  const roofSaid = roofShape === roof ? roofNote(roof, roofSource) : null;
  const eavesSaid = eaves === eavesAtStart ? eavesNote(eavesM, eavesSource, ridge) : null;

  return (
    <section ref={box} className="panel element-form" aria-labelledby={field('heading')}>
      <h2 id={field('heading')}>{heading}</h2>

      <label htmlFor={field('kind')}>Art</label>
      <select id={field('kind')} value={chosen} onChange={(e) => setChosen(e.target.value)}>
        {KINDS.map((k) => (
          <option key={k.kind} value={k.kind}>{k.label}</option>
        ))}
      </select>

      {chosen !== PLANTING_KIND && (
        <>
          <label htmlFor={field('height')}>Höhe (m)</label>
          <input id={field('height')} type="number" min="0" step="0.1" value={tall}
                 onChange={(e) => setTall(e.target.value)} />
        </>
      )}

      {ROOFED.has(chosen) && (
        <>
          <label htmlFor={field('roof')}>Dachform</label>
          <select id={field('roof')} value={roofShape} onChange={(e) => setRoofShape(e.target.value)}
                  aria-describedby={roofSaid === null ? undefined : field('roof-said')}>
            {ROOFS.map(([value, words]) => (
              <option key={value} value={value}>{words}</option>
            ))}
          </select>
          {roofSaid !== null && <p id={field('roof-said')} className="hint">{roofSaid}</p>}
          {/* Optional, and worth asking for: with the ridge it gives the pitch,
              and the pitch is what makes the north side of a roof darker than
              the south side. Without it the model assumes the eaves are three
              quarters of the way up. */}
          <label htmlFor={field('eaves')}>Traufhöhe (m)</label>
          <input id={field('eaves')} type="number" min="0" step="0.1" placeholder="geschätzt"
                 value={eaves} onChange={(e) => setEaves(e.target.value)}
                 aria-describedby={eavesSaid === null ? undefined : field('eaves-said')} />
          {eavesSaid !== null && <p id={field('eaves-said')} className="hint">{eavesSaid}</p>}

          {/* Said where the choice is made: the height came from the map and
              means the ridge, so a house without a shape shades as though its
              gables were solid. */}
          <p className="hint">
            Die Höhe aus der Karte ist der First; die Traufe ist, wo das Dach
            anfängt. Ohne Dachform rechnen wir das Haus bis zum First als massiv
            — es verschattet dann zu viel, und die Nordseite des Dachs bekommt
            nicht weniger Sonne als die Südseite.
          </p>
        </>
      )}

      {shape === 'line' && (
        <>
          <label htmlFor={field('width')}>Breite (m)</label>
          <input id={field('width')} type="number" min="0.05" step="any" value={band}
                 onChange={(e) => setBand(e.target.value)} />
        </>
      )}

      {chosen === PLANTING_KIND && (
        <>
          <label htmlFor={field('raised')}>Höhe über Grund (m)</label>
          <input id={field('raised')} type="number" min="0" step="0.1" value={raised}
                 onChange={(e) => setRaised(e.target.value)} />

          <label htmlFor={field('soil')}>Boden</label>
          <select id={field('soil')} value={soil} onChange={(e) => setSoil(e.target.value)}>
            <option value="">wie im Garten</option>
            <option value="sand">sandig</option>
            <option value="loam">lehmig</option>
            <option value="clay">tonig</option>
            <option value="humus">humos</option>
          </select>

          <label htmlFor={field('moisture')}>Feuchte</label>
          <select id={field('moisture')} value={wet} onChange={(e) => setWet(e.target.value)}>
            <option value="">wie im Garten</option>
            <option value="dry">trocken</option>
            <option value="fresh">frisch</option>
            <option value="moist">feucht</option>
            <option value="wet">nass</option>
          </select>
        </>
      )}

      <label htmlFor={field('label')}>Bezeichnung</label>
      <input
        id={field('label')}
        type="text"
        value={text}
        placeholder="z. B. Die Buche vom Nachbarn"
        onChange={(e) => setText(e.target.value)}
      />

      {confirming && plantings > 0 && (
        <p className="hint element-form__warning" role="alert">
          Hier {plantings === 1 ? 'steht eine Pflanze' : `stehen ${plantings} Pflanzen`}.
          {plantings === 1 ? ' Sie geht' : ' Sie gehen'} mit verloren.
        </p>
      )}

      <div className="element-form__actions">
        {confirming ? (
          <>
            <button
              type="button"
              className="element-form__danger"
              aria-disabled={busy || undefined}
              onClick={unlessBusy(onDelete)}
            >
              Endgültig löschen
            </button>
            <button type="button" className="link-button" onClick={() => setConfirming(false)}>
              Doch nicht
            </button>
          </>
        ) : (
          <>
            <button type="button" aria-disabled={busy || undefined} onClick={unlessBusy(save)}>
              Übernehmen
            </button>
            <button
              type="button"
              className="link-button element-form__delete"
              aria-disabled={busy || undefined}
              onClick={unlessBusy(() => setConfirming(true))}
            >
              Löschen
            </button>
            <button type="button" className="link-button" onClick={onCancel}>
              Abbrechen
            </button>
          </>
        )}
      </div>
    </section>
  );
}
