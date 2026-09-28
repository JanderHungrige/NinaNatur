import type { GardenOut } from '../api/client';
import { formValues } from '../garden/selection';
import type { GardenController } from '../garden/useGarden';
import { heightNote } from '../heights';
import { KINDS, labelOf } from '../kinds';
import { ElementForm } from './ElementForm';
import { areaOf } from './ElementList';
import { InspectorSubject, squareMetres } from './InspectorSubject';
import { ShadowMarkPanel } from './ShadowMarkPanel';

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

/** Whether this element casts a shadow the model draws: it stands up, and has a
 *  height somebody gave it. Mirrors `garden/casting.py::casts`. */
function casts(element: Obstacle): boolean {
  return element.height !== null && (KINDS.find((k) => k.kind === element.kind)?.standing ?? false);
}

/** The details of an element that is not a bed (doc 88): what it is, the form to
 *  say so, and — for a thing that casts, or has marks — where its shadow was
 *  seen to end. */
export function ElementDetails({ element, controller, busy }: Props) {
  const { elements, marks } = controller;
  const id = element.obstacle_id;
  const armed = elements.tool === 'shadowmark' && marks.target === id;
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
      {(casts(element) || marks.marks.some((mark) => mark.element_id === id)) && (
        <ShadowMarkPanel
          elementId={id}
          canMark={casts(element)}
          marks={marks.marks}
          seenAt={marks.seenAt}
          onSeenAt={marks.setSeenAt}
          armed={armed}
          onToggle={() => (armed ? marks.disarm() : marks.arm(id))}
          onRemove={marks.remove}
          busy={busy}
        />
      )}
    </>
  );
}
