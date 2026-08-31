import type { Tool } from '../canvas/shapes';

interface Props {
  active: Tool | null;
  onPick: (tool: Tool | null) => void;
  disabled: boolean;
}

const TOOLS: Array<{ tool: Tool; label: string; hint: string }> = [
  { tool: 'rect', label: 'Rechteck', hint: 'Aufziehen. Ecken bleiben rechtwinklig.' },
  { tool: 'circle', label: 'Kreis', hint: 'Aufziehen — die kleinere Seite ist der Durchmesser.' },
  { tool: 'triangle', label: 'Dreieck', hint: 'Aufziehen.' },
  { tool: 'polygon', label: 'Vieleck', hint: 'Ecke für Ecke klicken, dann „Fertig".' },
  { tool: 'freehand', label: 'Freihand', hint: 'In einem Zug ziehen — der Plan glättet die Linie.' },
];

/**
 * What you draw with.
 *
 * Separate from the kind: a shape is drawn first and named afterwards, which is
 * the order the user asked for and the one every drawing tool uses. Wave 10's
 * palette bound the two together, so a pond could only ever be a circle.
 */
export function ShapeTools({ active, onPick, disabled }: Props) {
  const chosen = TOOLS.find((t) => t.tool === active);
  return (
    <section className="panel shape-tools" aria-labelledby="tools-heading">
      <h2 id="tools-heading">Zeichnen</h2>
      <div role="group" aria-label="Formen" className="shape-tools__row">
        {TOOLS.map(({ tool, label }) => (
          <button
            key={tool}
            type="button"
            className="shape-tool"
            aria-pressed={active === tool}
            disabled={disabled}
            // The same click that arms a tool is the one reached for to stop.
            onClick={() => onPick(active === tool ? null : tool)}
          >
            {label}
          </button>
        ))}
      </div>
      <p className="hint" aria-live="polite">
        {chosen === undefined
          ? 'Wähle eine Form und zieh sie im Plan auf. Danach klickst du sie an und sagst, was sie ist.'
          : chosen.hint}
      </p>
    </section>
  );
}
