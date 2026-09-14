import type { GardenOut } from '../api/client';
import type { GardenController } from '../garden/useGarden';
import type { AccountInfo } from './AccountPanel';
import { BedPanel } from './BedPanel';
import { BedPlantings } from './BedPlantings';
import { CanopyBox } from './CanopyBox';
import { ColourNote } from './ColourNote';
import { ElementList } from './ElementList';
import { ExistingPlanting } from './ExistingPlanting';
import { FilterBar } from './FilterBar';
import { FilterControls } from './FilterControls';
import { GardenSoil } from './GardenSoil';
import { InsectScore } from './InsectScore';
import { ShadeSwitch } from './ShadeSwitch';
import { Sightlines } from './Sightlines';
import { SpeciesInfo } from './SpeciesInfo';
import { SuggestionList } from './SuggestionList';

interface Props {
  garden: GardenOut;
  controller: GardenController;
  account: AccountInfo | null;
  busy: boolean;
}

/**
 * Everything the details hold, in one column (doc 87): the garden, its elements,
 * and the bed → species loop. Feature 2 (doc 88) makes the selection decide which
 * of these is shown; until then they stand in the order a garden is worked on.
 */
export function InspectorPanels({ garden, controller, account, busy }: Props) {
  const { derived, elements, light, suggestions } = controller;
  const { selectedBedId, infoFor, filters } = suggestions;
  const recorded = (taxonId: number) => derived.resolvedColours[taxonId] ?? null;
  const bed = garden.beds.find((b) => b.bed_id === selectedBedId);

  return (
    <>
      <GardenSoil
        soilType={garden.soil_type}
        moisture={garden.moisture}
        onSave={elements.saveGardenSoil}
        busy={busy}
      />
      {account !== null ? (
        <button type="button" className="link-button" onClick={elements.claim}>
          Diesen Garten meinem Konto zuordnen
        </button>
      ) : null}
      {light.sightlines !== null ? (
        <Sightlines result={light.sightlines} onClear={light.clearSightlines} />
      ) : null}
      <BedPanel garden={garden} selectedBedId={selectedBedId} onSelectBed={suggestions.selectBed} />
      <CanopyBox
        suggestions={derived.canopies}
        busy={busy}
        onAccept={derived.acceptCanopy}
        onDismiss={derived.dismissCanopy}
      />
      <ShadeSwitch
        map={derived.lightMap}
        terrain={derived.terrain}
        on={light.shadeOn}
        mode={light.mapMode}
        month={light.mapMonth}
        onMonth={light.changeMonth}
        onToggle={light.toggleShade}
        onMode={light.setMapMode}
        onRebuild={light.rebuild}
        busy={busy}
        showToggle={false}
      />
      <ElementList
        garden={garden}
        onDelete={elements.deleteElement}
        selectedId={elements.selectedObstacleId ?? selectedBedId}
        onSelect={controller.selectElement}
      />

      {bed !== undefined ? (
        <>
          <BedPlantings
            bed={bed}
            onRemove={suggestions.removePlanting}
            onShowInfo={(taxonId, name) => suggestions.showInfo(taxonId, name, recorded(taxonId))}
            busy={busy}
          />
          <ExistingPlanting
            onAdd={suggestions.addExisting}
            unidentified={garden.unidentified_plantings}
            busy={busy}
          />
        </>
      ) : null}

      <FilterControls filters={filters} onChange={suggestions.changeFilters} disabled={busy} />
      <FilterBar
        filters={filters}
        counts={suggestions.suggestions?.filters ?? {}}
        onChange={suggestions.changeFilters}
      />
      {infoFor !== null ? (
        <SpeciesInfo
          taxonId={infoFor.taxonId}
          canonicalName={infoFor.name}
          onClose={suggestions.closeInfo}
          colourNote={
            <ColourNote
              recorded={infoFor.recorded}
              noted={infoFor.noted}
              busy={busy}
              onNote={suggestions.noteColour}
            />
          }
        />
      ) : null}
      <SuggestionList
        includeTrees={filters.includeTrees !== false}
        suggestions={suggestions.suggestions}
        onPlant={suggestions.plant}
        onShowInfo={suggestions.showInfo}
        busy={busy}
      />
      {derived.score !== null ? (
        <InsectScore
          score={derived.score}
          improvements={derived.improvements}
          onApply={suggestions.applyChange}
          busy={busy}
        />
      ) : null}
    </>
  );
}
