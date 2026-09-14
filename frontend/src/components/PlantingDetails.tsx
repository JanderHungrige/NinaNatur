import type { GardenOut } from '../api/client';
import type { GardenController } from '../garden/useGarden';
import { nameOf } from './BedPlantings';
import { ColourNote } from './ColourNote';
import { InspectorSubject } from './InspectorSubject';
import { SpeciesInfo } from './SpeciesInfo';

type Bed = GardenOut['beds'][number];
type Planting = Bed['plantings'][number];

interface Props {
  garden: GardenOut;
  planting: Planting;
  bed: Bed;
  controller: GardenController;
  busy: boolean;
}

/** "in Südbeet · 3 Pflanzen · nicht im Katalog" */
export function plantingDetail(planting: Planting, bed: Bed): string {
  const parts = [`in ${bed.name}`];
  if (planting.quantity > 1) parts.push(`${planting.quantity} Pflanzen`);
  // Said, not hidden: a plant the catalogue cannot name still stands in the bed,
  // but it counts for nothing in the insect score.
  if (planting.taxon_id === null) parts.push('nicht im Katalog');
  return parts.join(' · ');
}

/**
 * The details of a patch of plants (doc 88): what grows there, from the
 * catalogue and from Wikipedia. Already beside the plan, the article neither
 * scrolls to itself nor takes the focus from the patch that was chosen.
 */
export function PlantingDetails({ garden, planting, bed, controller, busy }: Props) {
  const { derived, suggestions } = controller;
  const name = nameOf(planting);
  const taxonId = planting.taxon_id;
  const toBed = () => controller.selectElement(bed.bed_id);

  return (
    <>
      <InspectorSubject
        title={name}
        detail={plantingDetail(planting, bed)}
        back={{ label: `Zurück zu ${bed.name}`, onBack: toBed }}
      />
      {taxonId !== null ? (
        <SpeciesInfo
          taxonId={taxonId}
          canonicalName={name}
          onClose={toBed}
          load={controller.speciesInfo}
          takeFocus={false}
          colourNote={
            <ColourNote
              recorded={derived.resolvedColours[taxonId] ?? null}
              noted={garden.observed_colours[taxonId] ?? null}
              busy={busy}
              onNote={(colour) => suggestions.noteColour(taxonId, colour)}
            />
          }
        />
      ) : (
        <div className="panel">
          <p className="hint">
            Diese Pflanze kennt der Katalog nicht. Sie steht im Plan, zählt aber nicht
            in den Insektenwert und nicht ins Blühjahr — dort fehlen uns die Daten.
          </p>
        </div>
      )}
    </>
  );
}
