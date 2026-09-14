import { type RefObject, useLayoutEffect, useRef } from 'react';

import type { GardenOut } from '../api/client';
import { viewKey } from '../garden/selection';
import type { GardenController } from '../garden/useGarden';
import type { AccountInfo } from './AccountPanel';
import { BedDetails } from './BedDetails';
import { ElementDetails } from './ElementDetails';
import { GardenDetails } from './GardenDetails';
import { PlantingDetails } from './PlantingDetails';
import { Sightlines } from './Sightlines';

interface Props {
  garden: GardenOut;
  controller: GardenController;
  account: AccountInfo | null;
  busy: boolean;
}

/**
 * What the details show: the selection decides (doc 88).
 *
 * One view at a time — the garden while nothing is selected, or the bed, the
 * element or the patch that is. A viewpoint's answer stands above whichever view
 * it is, because it answers the last thing done on the plan rather than what is
 * selected.
 */
export function InspectorPanels({ garden, controller, account, busy }: Props) {
  const { selection, light } = controller;
  const view = useRef<HTMLDivElement | null>(null);
  useViewFocus(view, viewKey(selection));

  return (
    <div className="inspector__view" ref={view}>
      {light.sightlines !== null ? (
        <Sightlines result={light.sightlines} onClear={light.clearSightlines} />
      ) : null}

      {selection.kind === 'none' ? (
        <GardenDetails garden={garden} controller={controller} account={account} busy={busy} />
      ) : null}
      {selection.kind === 'bed' ? (
        <BedDetails
          key={selection.bed.bed_id}
          garden={garden}
          bed={selection.bed}
          controller={controller}
          busy={busy}
        />
      ) : null}
      {selection.kind === 'element' ? (
        <ElementDetails
          key={selection.element.obstacle_id}
          element={selection.element}
          controller={controller}
          busy={busy}
        />
      ) : null}
      {selection.kind === 'planting' ? (
        <PlantingDetails
          key={selection.planting.planting_id}
          garden={garden}
          planting={selection.planting}
          bed={selection.bed}
          controller={controller}
          busy={busy}
        />
      ) : null}
    </div>
  );
}

/**
 * Where the focus goes when the view changes (doc 88): to the new view's heading
 * if it was in the details — or was lost with the view it was in — and nowhere
 * if it was anywhere else. Choosing on the plan never pulls the keyboard off it.
 */
function useViewFocus(view: RefObject<HTMLDivElement | null>, key: string): void {
  const shown = useRef(key);

  useLayoutEffect(() => {
    if (shown.current === key) return;
    shown.current = key;
    const root = view.current;
    if (root === null) return;
    const active = document.activeElement;
    const lost = active === null || active === document.body || !active.isConnected;
    if (!lost && !root.contains(active)) return;
    root.querySelector<HTMLElement>('[data-view-heading]')?.focus();
  }, [view, key]);
}
