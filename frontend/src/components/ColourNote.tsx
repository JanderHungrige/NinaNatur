import { COLOURS } from '../colours';


interface Props {
  /** What the catalogue says, if anything. */
  recorded: string | null;
  /** What this garden has noted, if anything. */
  noted: string | null;
  onNote: (colour: string | null) => void;
  busy: boolean;
}

/**
 * Recording a flower colour from the photograph.
 *
 * Colour is recorded for 590 of 8,939 species, so most of the catalogue has
 * nothing to say — and somebody looking at the picture, or at their own bed,
 * usually can.
 *
 * It is stored against this garden, never against the catalogue. The catalogue
 * ships in the image and is re-synced on deployment, so a value written there
 * would be overwritten by the next release and would change every other
 * garden's plan until it was.
 */
export function ColourNote({ recorded, noted, onNote, busy }: Props) {
  const shown = noted ?? recorded ?? '';

  return (
    <div className="colour-note">
      <label htmlFor="colour-note">Blütenfarbe</label>
      <select
        id="colour-note"
        value={shown}
        disabled={busy}
        onChange={(e) => onNote(e.target.value === '' ? null : e.target.value)}
      >
        <option value="">
          {recorded === null ? 'nicht erfasst' : 'wie im Katalog'}
        </option>
        {COLOURS.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      {/* Said before the entry, not after: it goes into the shared catalogue
          and answers for every garden here, which somebody should know while
          they are deciding what to type. */}
      <p className="hint">
        {noted !== null
          ? recorded !== null && recorded !== noted
            ? `Von Hand eingetragen — eine Quelle sagt inzwischen „${recorded}“, und die gilt.`
            : 'Von Hand eingetragen. Gilt für alle Gärten hier, bis eine Quelle etwas anderes sagt.'
          : recorded !== null
            ? 'Aus einer Quelle. Eine Handeingabe würde dahinter zurückstehen.'
            : 'Für diese Art ist keine Farbe erfasst. Trag ein, was du auf dem Bild oder im Beet siehst — es hilft allen hier.'}
      </p>
    </div>
  );
}
