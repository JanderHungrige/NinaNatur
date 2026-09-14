import type { GardenOut } from '../api/client';
import type { GardenController } from '../garden/useGarden';
import type { AccountInfo } from './AccountPanel';
import { BedPanel } from './BedPanel';
import { CanopyBox } from './CanopyBox';
import { ElementList } from './ElementList';
import { InsectScore } from './InsectScore';
import { ShadeSwitch } from './ShadeSwitch';
import { SoilLine } from './SoilLine';

interface Props {
  garden: GardenOut;
  controller: GardenController;
  account: AccountInfo | null;
  busy: boolean;
}

/**
 * The details while nothing is selected: the garden itself (doc 88).
 *
 * Its beds to choose from, the soil in one line, the sun map's settings, the
 * insect score, the trees found nearby and everything drawn. The bloom year is
 * not repeated here: the dock under the plan shows it whatever is selected.
 */
export function GardenDetails({ garden, controller, account, busy }: Props) {
  const { derived, elements, light, suggestions } = controller;

  return (
    <>
      <BedPanel garden={garden} selectedBedId={null} onSelectBed={controller.selectElement} />
      <SoilLine
        soilType={garden.soil_type}
        moisture={garden.moisture}
        onSave={elements.saveGardenSoil}
        busy={busy}
      />
      {account !== null ? (
        <button type="button" className="link-button inspector__action" onClick={elements.claim}>
          Diesen Garten meinem Konto zuordnen
        </button>
      ) : null}
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
      {derived.score !== null ? (
        <InsectScore
          score={derived.score}
          improvements={derived.improvements}
          onApply={suggestions.applyChange}
          busy={busy}
        />
      ) : null}
      <CanopyBox
        suggestions={derived.canopies}
        busy={busy}
        onAccept={derived.acceptCanopy}
        onDismiss={derived.dismissCanopy}
      />
      <ElementList
        garden={garden}
        selectedId={null}
        onSelect={controller.selectElement}
        onDelete={elements.deleteElement}
      />
    </>
  );
}
