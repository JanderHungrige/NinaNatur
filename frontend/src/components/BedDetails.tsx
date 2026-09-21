import { useState } from 'react';

import type { GardenOut } from '../api/client';
import { formValues } from '../garden/selection';
import type { GardenController } from '../garden/useGarden';
import { labelOf } from '../kinds';
import { lightText } from './BedPanel';
import { BedPlantings } from './BedPlantings';
import { ColourNote } from './ColourNote';
import { ElementForm } from './ElementForm';
import { areaOf } from './ElementList';
import { ExistingPlanting } from './ExistingPlanting';
import { FilterBar } from './FilterBar';
import { FilterControls } from './FilterControls';
import { InspectorSubject, squareMetres } from './InspectorSubject';
import { SpeciesInfo } from './SpeciesInfo';
import { SuggestionList } from './SuggestionList';

type Bed = GardenOut['beds'][number];

interface Props {
  garden: GardenOut;
  bed: Bed;
  controller: GardenController;
  busy: boolean;
}

/** "Blumenbeet, 6,0 m² · 6.4 h/Tag · L 8": what it is, what it covers, what light it gets. */
export function bedDetail(bed: Bed): string {
  const what =
    bed.label !== null && bed.label !== '' ? `${labelOf(bed.kind)} — ${bed.label}` : labelOf(bed.kind);
  return `${what}, ${squareMetres(areaOf(bed.polygon))} · ${lightText(bed)}`;
}

/**
 * The details of a bed (doc 88): what it is, its own values folded away, what
 * stands in it and what could — the loop the workspace exists for.
 */
export function BedDetails({ garden, bed, controller, busy }: Props) {
  const { derived, elements, suggestions } = controller;
  const { infoFor, filters } = suggestions;
  const asked = controller.askedFor === bed.bed_id;
  // Folded away: planting is what a bed is chosen for. A question asked about
  // the bed from the plan unfolds it, even while the bed is already showing.
  const [editing, setEditing] = useState(asked);
  if (asked && !editing) setEditing(true);

  const loaded =
    suggestions.suggestions !== null && suggestions.suggestions.bed_id === bed.bed_id
      ? suggestions.suggestions
      : null;
  const recorded = (taxonId: number) => derived.resolvedColours[taxonId] ?? null;

  return (
    <>
      <InspectorSubject
        title={bed.name}
        detail={bedDetail(bed)}
        back={{ label: 'Zurück zum Garten', onBack: controller.clearSelection }}
      />
      <button
        type="button"
        className="link-button inspector__action"
        aria-expanded={editing}
        onClick={() => setEditing(!editing)}
      >
        Beet bearbeiten
      </button>
      {editing ? (
        <ElementForm
          {...formValues(bed)}
          heading="Was ist das?"
          busy={busy}
          takeFocus={asked}
          onFocusTaken={controller.focusTaken}
          onSave={(changes) => elements.saveElement(bed.bed_id, changes)}
          onDelete={() => elements.deleteElement(bed.bed_id)}
          onCancel={() => setEditing(false)}
        />
      ) : null}

      <BedPlantings
        bed={bed}
        onRemove={suggestions.removePlanting}
        onShowInfo={(taxonId, name) => suggestions.showInfo(taxonId, name, recorded(taxonId))}
        busy={busy}
      />
      {infoFor !== null ? (
        <SpeciesInfo
          taxonId={infoFor.taxonId}
          canonicalName={infoFor.name}
          onClose={suggestions.closeInfo}
          load={controller.speciesInfo}
          colourNote={
            <ColourNote
              recorded={infoFor.recorded}
              noted={garden.observed_colours[infoFor.taxonId] ?? null}
              busy={busy}
              onNote={(colour) => suggestions.noteColour(infoFor.taxonId, colour)}
            />
          }
        />
      ) : null}

      {loaded !== null ? (
        <SuggestionList
          includeTrees={filters.includeTrees !== false}
          suggestions={loaded}
          onPlant={suggestions.plant}
          onShowInfo={suggestions.showInfo}
          busy={busy}
          onComputeShade={controller.computeShade}
          filters={
            <>
              <FilterBar
                filters={filters}
                counts={loaded.filters ?? {}}
                onChange={suggestions.changeFilters}
              />
              <details className="filters-disclosure">
                <summary>Filter</summary>
                <FilterControls filters={filters} onChange={suggestions.changeFilters} busy={busy} />
              </details>
            </>
          }
        />
      ) : (
        <section className="panel" aria-labelledby="suggestions-waiting">
          <h2 id="suggestions-waiting">Vorschläge</h2>
          <p className="hint">
            {suggestions.failedFor === bed.bed_id
              ? 'Die Vorschläge für dieses Beet konnten nicht geladen werden.'
              : 'Die Vorschläge für dieses Beet werden geladen…'}
          </p>
        </section>
      )}

      <ExistingPlanting
        onAdd={suggestions.addExisting}
        unidentified={garden.unidentified_plantings}
        busy={busy}
      />
    </>
  );
}
