import type { GardenOut } from '../api/client';
import type { GardenController } from '../garden/useGarden';
import { GardenCanvas } from './GardenCanvas';
import { hintFor } from './ToolRail';

interface Props {
  garden: GardenOut;
  controller: GardenController;
}

/**
 * The plan in the middle of the workspace (docs 87, 88): the canvas filling its
 * cell, zoom and scale over its corner, and what the armed tool expects.
 *
 * What is selected comes from the one selection. Right-click, Shift+F10 and the
 * context-menu key ask about an element, and the answer is given in the details
 * beside the plan rather than in a menu over it.
 */
export function PlanArea({ garden, controller }: Props) {
  const { derived, elements, geometry, light, suggestions, clipboard, ids } = controller;

  return (
    <div className="workspace__plan">
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
        sunMap={
          light.shadeOn && derived.lightMap !== null
            ? { map: derived.lightMap, mode: light.mapMode }
            : undefined
        }
        // Only in day mode: `day` is null in the other two, which is what keeps
        // the heat maps free of obstacle shadows.
        shadows={light.day?.frames[light.frame]?.polygons ?? undefined}
        viewpoint={light.viewpoint}
        onPlaceViewpoint={light.lookFrom}
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
      />

      {/* The hints the drawing panel used to carry, over the plan they are about. */}
      <p className="plan-hint" aria-live="polite">
        {hintFor(elements.tool)}
      </p>
    </div>
  );
}
