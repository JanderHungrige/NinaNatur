import type { GardenOut } from '../api/client';
import type { GardenController } from '../garden/useGarden';
import { BedPanel } from './BedPanel';
import { CanopyBox } from './CanopyBox';
import { DayPlayer } from './DayPlayer';
import { ElementList } from './ElementList';
import { FirstSteps, stepsDone } from './FirstSteps';
import { InsectScore } from './InsectScore';
import { ShadeSwitch } from './ShadeSwitch';
import { Skeleton } from './Skeleton';
import { SoilLine } from './SoilLine';
import { SourceCredits } from './SourceCredits';

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
 *
 * While the garden's answers are still on their way, quiet placeholders hold
 * the places of the panels they decide — the steps or the soil line, the sun
 * and the insect score — so nothing jumps in under the reader once they land.
 */
export function GardenDetails({ garden, controller, busy }: Props) {
  const { derived, elements, light, suggestions } = controller;
  const steps = stepsDone(garden, derived.lightMap);

  return (
    <>
      <BedPanel garden={garden} selectedBedId={null} onSelectBed={controller.selectElement} />
      {derived.loading ? (
        // Which of the two stands here depends on the map, which has not come yet.
        <Skeleton of="steps" lines={2} />
      ) : steps.all ? (
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
          computing={light.rebuilding}
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
          rebuilding={light.rebuilding}
          monthWorking={light.monthLoading}
          dayPlayer={<DayPlayer watch={light.day} />}
        />
      ) : derived.loading ? (
        <Skeleton of="shade" />
      ) : null}
      {derived.score !== null ? (
        <InsectScore
          score={derived.score}
          improvements={derived.improvements}
          onApply={suggestions.applyChange}
          busy={busy}
        />
      ) : derived.loading ? (
        <Skeleton of="score" />
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
      {/* Last, because it is about everything above it: which survey said so,
          and the credit each licence asks for (doc 106). */}
      <SourceCredits credits={derived.sources} />
    </>
  );
}
