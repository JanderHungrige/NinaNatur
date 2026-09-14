import type { GardenOut } from '../api/client';
import { formValues } from '../garden/selection';
import type { GardenController } from '../garden/useGarden';
import { heightNote } from '../heights';
import { labelOf } from '../kinds';
import { ElementForm } from './ElementForm';
import { areaOf } from './ElementList';
import { InspectorSubject, squareMetres } from './InspectorSubject';

type Obstacle = GardenOut['obstacles'][number];

interface Props {
  element: Obstacle;
  controller: GardenController;
  busy: boolean;
}

/** "Schuppen, 4,0 m² · 2,4 m hoch": the element list's words for the same element. */
export function elementDetail(element: Obstacle): string {
  const parts = [`${labelOf(element.kind)}, ${squareMetres(areaOf(element.footprint))}`];
  if (element.height !== null) parts.push(`${element.height.toFixed(1).replace('.', ',')} m hoch`);
  // Where the height came from. A shading map resting on an assumption must not
  // look like one resting on a measurement.
  const note = heightNote(element.height_source);
  if (note !== null) parts.push(note);
  return parts.join(' · ');
}

/** The details of an element that is not a bed (doc 88): what it is, and the form to say so. */
export function ElementDetails({ element, controller, busy }: Props) {
  const { elements } = controller;
  const id = element.obstacle_id;
  // The gardener's own words first, when there are any: it is what they call the thing.
  const title =
    element.label !== null && element.label !== '' ? element.label : labelOf(element.kind);

  return (
    <>
      <InspectorSubject
        title={title}
        detail={elementDetail(element)}
        back={{ label: 'Zurück zum Garten', onBack: controller.clearSelection }}
      />
      <ElementForm
        {...formValues(element)}
        heading="Was ist das?"
        busy={busy}
        takeFocus={controller.askedFor === id}
        onFocusTaken={controller.focusTaken}
        onSave={(changes) => elements.saveElement(id, changes)}
        onDelete={() => elements.deleteElement(id)}
        onCancel={controller.clearSelection}
      />
    </>
  );
}
