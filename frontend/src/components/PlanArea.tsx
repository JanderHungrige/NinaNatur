import type { GardenOut } from '../api/client';
import type { GardenController } from '../garden/useGarden';
import { ElementMenu } from './ElementMenu';
import { GardenCanvas } from './GardenCanvas';
import { hintFor } from './ToolRail';

interface Props {
  garden: GardenOut;
  controller: GardenController;
  busy: boolean;
}

/**
 * The plan in the middle of the workspace (doc 87): the canvas filling its cell,
 * zoom and scale over its corner, what the armed tool expects, and the menu that
 * asks what an element is.
 */
export function PlanArea({ garden, controller, busy }: Props) {
  const { derived, elements, geometry, light, suggestions, clipboard } = controller;
  const { asking } = elements;

  return (
    <div className="workspace__plan">
      <GardenCanvas
        garden={garden}
        selectedBedId={suggestions.selectedBedId}
        onSelectBed={suggestions.selectBed}
        onDrawBed={elements.drawBed}
        onSelectObstacle={elements.editObstacleById}
        clusters={suggestions.clusters}
        selectedPlantingId={clipboard.selectedPlantingId}
        onSelectCluster={clipboard.setSelectedPlantingId}
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
        onShowClusterInfo={(taxonId, name) =>
          suggestions.showInfo(taxonId, name, derived.resolvedColours[taxonId] ?? null)
        }
        viewpoint={light.viewpoint}
        onPlaceViewpoint={light.lookFrom}
        tool={elements.tool}
        onDrawShape={elements.drawShape}
        onDrawTrace={elements.drawTrace}
        onCancelTool={() => elements.setTool(null)}
        onClearSelection={controller.clearSelection}
        onAskWhatItIs={elements.askWhatItIs}
        selectedObstacleId={elements.selectedObstacleId}
        onResizeObstacle={geometry.resizeObstacle}
        onMoveObstacle={geometry.moveObstacle}
        onReshapeObstacle={geometry.reshapeObstacle}
      />

      {/* The hints the drawing panel used to carry, over the plan they are about. */}
      <p className="plan-hint" aria-live="polite">
        {hintFor(elements.tool)}
      </p>

      {asking !== null ? (
        <ElementMenu
          elementId={asking.id}
          at={asking.at}
          kind={asking.kind}
          label={asking.label}
          area={asking.area}
          plantings={asking.plantings}
          shape={asking.shape}
          roof={asking.roof}
          eavesM={asking.eavesM}
          height={asking.height}
          width={asking.width}
          soilType={asking.soilType}
          moisture={asking.moisture}
          heightAboveGround={asking.heightAboveGround}
          busy={busy}
          onDelete={() => elements.deleteElement(asking.id)}
          onClose={() => elements.setAsking(null)}
          onSave={elements.saveElement}
        />
      ) : null}
    </div>
  );
}
