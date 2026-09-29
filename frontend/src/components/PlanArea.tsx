import type { GardenOut } from '../api/client';
import type { GardenController } from '../garden/useGarden';
import { GardenCanvas } from './GardenCanvas';
import { PlanWorking } from './PlanWorking';
import { hintFor } from './ToolRail';

interface Props {
  garden: GardenOut;
  controller: GardenController;
  /** Whether the plan's credits stand beneath it: not on a phone, where they
   *  close the details instead and the map is marked in the drawing's corner
   *  (the owner, 2026-09-29). */
  creditsBelow: boolean;
}

/**
 * The plan in the middle of the workspace (docs 87, 88): the canvas filling its
 * cell, zoom and scale over its corner, and what the armed tool expects.
 *
 * What is selected comes from the one selection. Right-click, Shift+F10 and the
 * context-menu key ask about an element, and the answer is given in the details
 * beside the plan rather than in a menu over it.
 *
 * While the shade is computed a sweep of light lies over the plan, and while a
 * month's map is on its way the old one is dimmed — both from here, around the
 * canvas, so nothing inside the drawing has to know (doc 65).
 */
export function PlanArea({ garden, controller, creditsBelow }: Props) {
  const { derived, elements, geometry, light, marks, suggestions, clipboard, ids } = controller;
  const waiting = light.shadeOn && light.monthLoading;

  return (
    <div className={waiting ? 'workspace__plan workspace__plan--waiting' : 'workspace__plan'}>
      <GardenCanvas
        garden={garden}
        selectedBedId={ids.bedId}
        onSelectBed={controller.selectElement}
        onDrawBed={elements.drawBed}
        onSelectObstacle={controller.selectElement}
        clusters={suggestions.clusters}
        selectedPlantingId={ids.plantingId}
        freshPlantingId={suggestions.freshPlantingId}
        onSelectCluster={controller.selectPlanting}
        onMoveCluster={clipboard.moveCluster}
        terrain={light.shadeOn ? derived.terrain : null}
        // The neighbourhood is not the shade's: it is there either way (doc 114).
        landcover={derived.landcover}
        creditsBelow={creditsBelow}
        sunMap={
          light.shadeOn && derived.lightMap !== null
            ? { map: derived.lightMap, mode: light.mapMode }
            : undefined
        }
        // Only in day mode: the day is null in the other two, which is what
        // keeps the heat maps free of obstacle shadows.
        shadows={light.day.shadows?.frames[light.day.frame]?.polygons ?? undefined}
        viewpoint={light.viewpoint}
        // One click on the plan places a point: where somebody stands (doc 89),
        // or where the armed element's shadow was seen to end (doc 122).
        onPlaceViewpoint={elements.tool === 'shadowmark' ? marks.place : light.lookFrom}
        shadowMarks={marks.marks}
        canopies={derived.canopies}
        onShowFoundTrees={controller.showFoundTrees}
        tool={elements.tool}
        onDrawShape={elements.drawShape}
        onDrawTrace={elements.drawTrace}
        onCancelTool={() => elements.setTool(null)}
        onClearSelection={controller.clearSelection}
        onAskWhatItIs={controller.askAbout}
        selectedObstacleId={ids.elementId}
        onResizeObstacle={geometry.resizeObstacle}
        onMoveObstacle={geometry.moveObstacle}
        onReshapeObstacle={geometry.reshapeObstacle}
        // The hints the drawing panel used to carry, over the plan they are
        // about — inside the drawing, above any caption under it.
        hint={hintFor(elements.tool)}
      />
      {light.rebuilding ? <PlanWorking /> : null}
    </div>
  );
}
