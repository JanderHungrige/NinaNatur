import { type ReactNode, useLayoutEffect, useRef } from 'react';

import type { BedSuggestions } from '../api/client';
import { focusLost, holdsFocus } from '../suggestions/focus';
import { hiddenByLight, lightHint, LightNote } from './SuggestionLight';
import { SuggestionWindow } from './SuggestionWindow';

interface Props {
  suggestions: BedSuggestions | null;
  /** Whether woody plants are listed — the hint used to claim they never were. */
  includeTrees: boolean;
  onPlant: (taxonId: number, name: string) => Promise<void>;
  /** The third argument is the catalogue's colour, so the panel can say
   *  whether what it shows came from there or from the gardener. */
  onShowInfo: (taxonId: number, name: string, colour: string | null) => void;
  busy: boolean;
  /** The filters — what is chosen, and the fields to choose with — in the
   *  list's header, above the rows (doc 90, rule 7). */
  filters?: ReactNode;
  /** „Schatten berechnen“: the sun panel's rebuild, offered where the list was
   *  ranked without the bed's light, or with an old one. */
  onComputeShade?: () => void;
}

/** "1.234 passende Arten", or how many of them the list holds when it holds
 *  fewer: the window ends at fifty, and its header should not promise the rest. */
function listed(shown: number, total: number): string {
  const all = total.toLocaleString('de-DE');
  if (shown >= total) return `${all} passende ${total === 1 ? 'Art' : 'Arten'}`;
  return shown === 1 ? `Die passendste von ${all} Arten` : `Die ${shown} passendsten von ${all} Arten`;
}

/**
 * A bed's suggestions (doc 90): a header that says what is listed and holds the
 * filters, the rows as a window that scrolls in itself, and the woody plants
 * under their own heading in a window of their own (doc 25).
 */
export function SuggestionList({
  suggestions, includeTrees, onPlant, onShowInfo, busy, filters, onComputeShade,
}: Props) {
  const section = useRef<HTMLElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const hadFocus = holdsFocus(section.current);

  // A list that goes away takes the focus with it: a bed's only woody
  // suggestion, planted. The heading catches it. A row that only left its list
  // is caught by its window, whose effect runs before this one.
  useLayoutEffect(() => {
    if (hadFocus && focusLost()) heading.current?.focus();
  });

  if (suggestions === null) {
    return (
      <section className="panel">
        <h2>Vorschläge</h2>
        <p className="hint">Wähle ein Beet, um passende Arten zu sehen.</p>
      </section>
    );
  }

  const rows = { busy, onPlant, onShowInfo };
  const showsBirds = [...suggestions.items, ...suggestions.woody].some(
    (i) => (i.bird_partners ?? 0) > 0,
  );
  const lightKnown = lightHint(suggestions.light_state) === null;
  const hidden = hiddenByLight(suggestions.filters ?? {});

  return (
    <section ref={section} className="panel suggestions" aria-labelledby="suggestions-heading">
      <div className="suggestions__header">
        <h2 id="suggestions-heading" ref={heading} tabIndex={-1}>
          Vorschläge für {suggestions.bed_name}
        </h2>
        <p className="hint">
          {listed(suggestions.items.length, suggestions.total)}
          {lightKnown ? ', gewertet nach den Standortwerten dieses Beetes. ' : '. '}
          {hidden !== null && `${hidden} `}
          {includeTrees
            ? 'Gehölze stehen weiter unten in einer eigenen Liste.'
            : 'Bäume und Sträucher sind ausgeblendet.'}
        </p>
        <LightNote state={suggestions.light_state} busy={busy} onComputeShade={onComputeShade} />
        {filters}
        {showsBirds && (
          <p className="hint">
            „Als Nahrung“ zählt Vogelarten, für die erfasst ist, dass sie diese
            Pflanze fressen — meist Früchte oder Samen. Die Zahl steht neben dem
            Insektenwert, nicht darin.
          </p>
        )}
      </div>

      <SuggestionWindow items={suggestions.items} label="Vorschläge" {...rows} />

      {suggestions.woody.length > 0 && (
        <>
          <h3>Gehölze für diesen Standort</h3>
          <p className="hint">
            Sträucher und Bäume passen selten in ein Beet und tragen am meisten —
            sie führen den Katalog bei Insekten wie bei Vögeln an. Was mehr Platz
            braucht, als dieses Beet hat, steht mit seinem Platzbedarf dabei. Ein
            gepflanztes Gehölz verschattet anschließend sein Beet und die
            Nachbarbeete, und die Vorschläge dort ändern sich entsprechend.
          </p>
          <SuggestionWindow items={suggestions.woody} label="Gehölze" {...rows} />
        </>
      )}
    </section>
  );
}
