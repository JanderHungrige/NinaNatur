import { crownBaseNote } from '../heights';

interface Props {
  /** The element form's id prefix, so the field's ids are its own. */
  id: string;
  /** The kind chosen in the form, and the kind the element was stored as. */
  kind: string;
  storedKind: string;
  /** What is stored, and who said it: 'user' | 'measured' | null. */
  storedM: number | null;
  storedSource: string | null;
  /** The height in the form, for the assumption's number; null when unreadable. */
  heightM: number | null;
  value: string;
  onChange: (value: string) => void;
}

/**
 * Where a tree's or shrub's crown starts (doc 121): under it, a low sun passes.
 *
 * The note says where the stored value came from, or what the model reckons
 * with when nobody gave one — and only while it describes what the field
 * shows: once the value is typed over, or the kind changed, it is the
 * gardener's and says nothing.
 */
export function CrownBaseField({
  id, kind, storedKind, storedM, storedSource, heightM, value, onChange,
}: Props) {
  const stored = storedM === null ? '' : String(storedM);
  const said = value === stored && kind === storedKind
    ? crownBaseNote(kind, storedM, storedSource, heightM) : null;
  return (
    <>
      <label htmlFor={`${id}-crown-base`}>Kronenansatz (m)</label>
      <input id={`${id}-crown-base`} type="number" min="0" step="0.1" placeholder="geschätzt"
             value={value} onChange={(e) => onChange(e.target.value)}
             aria-describedby={said === null ? undefined : `${id}-crown-base-said`} />
      {said !== null && <p id={`${id}-crown-base-said`} className="hint">{said}</p>}
    </>
  );
}
