export type Panel = 'draw' | 'sow';

interface Props {
  active: Panel;
  onPick: (panel: Panel) => void;
}

const TABS: Array<{ id: Panel; label: string; hint: string }> = [
  { id: 'draw', label: 'Zeichnen', hint: 'Formen aufziehen, benennen, den Boden festlegen' },
  { id: 'sow', label: 'Säen', hint: 'Pflanzen wählen, Blühjahr und Insektenwert' },
];

/**
 * The two things somebody is doing at a time.
 *
 * The sidebar had grown to nine panels stacked down one column — drawing tools,
 * soil, the element list, filters, suggestions, timeline, score. Nobody is
 * choosing a shape and reading a bloom timeline in the same breath.
 *
 * Real tabs rather than a menu: `role="tab"` with arrow keys is what a screen
 * reader and a keyboard already know how to drive.
 */
export function Tabs({ active, onPick }: Props) {
  const order: Panel[] = TABS.map((t) => t.id);

  return (
    <div className="tabs">
      <div className="tabs__row" role="tablist" aria-label="Bereich">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={active === tab.id}
            aria-controls={`panel-${tab.id}`}
            // Only the selected tab is in the tab order; the arrows move
            // between them. That is what a tablist is expected to do.
            tabIndex={active === tab.id ? 0 : -1}
            className="tabs__tab"
            onClick={() => onPick(tab.id)}
            onKeyDown={(event) => {
              const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
              if (step === 0) return;
              event.preventDefault();
              const next = order[(order.indexOf(active) + step + order.length) % order.length];
              if (next !== undefined) {
                onPick(next);
                document.getElementById(`tab-${next}`)?.focus();
              }
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <p className="hint tabs__hint">{TABS.find((t) => t.id === active)?.hint}</p>
    </div>
  );
}
