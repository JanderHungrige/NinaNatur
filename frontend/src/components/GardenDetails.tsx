import type { GardenOut } from '../api/client';
import type { GardenController } from '../garden/useGarden';
import { BedPanel } from './BedPanel';
import { CanopyBox } from './CanopyBox';
import { ElementList } from './ElementList';
import { FirstSteps, stepsDone } from './FirstSteps';
import { InsectScore } from './InsectScore';
import { ShadeSwitch } from './ShadeSwitch';
import { SoilLine } from './SoilLine';

interface Props {
  garden: GardenOut;
  controller: GardenController;
  busy: boolean;
}

/**
 * The details while nothing is selected: the garden itself (docs 88, 89).
 *
 * Its beds to choose from; the first three steps while the garden is not set up,
 * and the soil in one line once it is; the sun map's settings once there is a
 * map; the insect score; the trees found nearby; and everything drawn. The bloom
 * year is not repeated here: the dock under the plan shows it whatever is
 * selected.
 */
export function GardenDetails({ garden, controller, busy }: Props) {
  const { derived, elements, light, suggestions } = controller;
  const steps = stepsDone(garden, derived.lightMap);

  return (
    <>
      <BedPanel garden={garden} selectedBedId={null} onSelectBed={controller.selectElement} />
      {steps.all ? (
        <SoilLine
          soilType={garden.soil_type}
          moisture={garden.moisture}
          onSave={elements.saveGardenSoil}
          busy={busy}
        />
      ) : (
        <FirstSteps
          soilType={garden.soil_type}
          moisture={garden.moisture}
          onSaveSoil={elements.saveGardenSoil}
          hasMap={steps.shade}
          onComputeShade={light.rebuild}
          beds={garden.beds.length}
          onDrawBed={() => elements.setTool('polygon')}
          busy={busy}
        />
      )}
      {/* Without a map the panel's only content would be step 2's own button. */}
      {derived.lightMap !== null ? (
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
      ) : null}
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
        takeFocus={controller.treesAsked}
        onFocusTaken={controller.treesShown}
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
