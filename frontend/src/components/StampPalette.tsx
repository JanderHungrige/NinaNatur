import { type Kind, STANDING, SURFACES } from '../kinds';

interface Props {
  selected: string | null;
  onPick: (kind: string | null) => void;
  busy: boolean;
}

/**
 * The elements a plan is made of.
 *
 * Split into things that stand up and surfaces, because that is the difference
 * that matters: one group casts shadows and is drawn on top, the other does
 * neither. Sorting them by that rather than alphabetically means the grouping
 * teaches the distinction instead of hiding it.
 */
export function StampPalette({ selected, onPick, busy }: Props) {
  const button = (stamp: Kind) => (
    <button
      key={stamp.kind}
      type="button"
      className="stamp"
      aria-pressed={selected === stamp.kind}
      // Spelt out, because the two spans run together into "Wohnhaus10 × 8 m"
      // otherwise — one word to anything reading the name rather than the page.
      aria-label={`${stamp.label}, ${stamp.size}`}
      disabled={busy}
      // The same click that says "a house" is the one reached for to stop.
      onClick={() => onPick(selected === stamp.kind ? null : stamp.kind)}
    >
      <span className="stamp__label">{stamp.label}</span>
      <span className="stamp__size">{stamp.size}</span>
    </button>
  );

  return (
    <section className="panel stamp-palette" aria-labelledby="palette-heading">
      <h2 id="palette-heading">Elemente</h2>
      <p className="hint">
        Wähle ein Element und klicke in den Plan. Danach lässt es sich an den
        Griffen ziehen und drehen.
      </p>

      <div role="group" aria-label="Bauten und Pflanzen" className="stamp-palette__group">
        {STANDING.map(button)}
      </div>
      <div role="group" aria-label="Flächen" className="stamp-palette__group">
        {SURFACES.map(button)}
      </div>
    </section>
  );
}
